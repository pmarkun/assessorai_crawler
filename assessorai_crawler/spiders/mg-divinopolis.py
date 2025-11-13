import re
from datetime import datetime
import hashlib
from .base_sapl import BaseSaplSpider
from ..items import ProposicaoItem

class MgDivinopolisSpider(BaseSaplSpider):
    """
    Coleta proposições da Câmara Municipal de Divinópolis usando SAPL.
    """
    name = 'mg-divinopolis'
    house = 'Câmara Municipal de Divinópolis'
    uf = 'MG'
    slug = 'mg-divinopolis'
    domain = 'sapl.divinopolis.mg.leg.br'
    base_url = "https://sapl.divinopolis.mg.leg.br/materia/pesquisar-materia"

    # Tipos de documento específicos para Divinópolis
    TIPOS_DOCUMENTO = {
        14: "Projeto de Lei Ordinária do Executivo Municipal",
    }
    default_tipo = 14

    def parse(self, response):
        """Processa a página de listagem, extrai os itens e segue para a próxima página."""
        self.logger.info(f"Processando página de listagem: {response.url}")

        # Para Divinópolis, os resultados são em células de tabela
        materia_cells = response.css('tr td')
        self.logger.info(f"Encontradas {len(materia_cells)} matérias para processar nesta página.")

        for cell in materia_cells:
            item = self.extract_metadata_from_cell(cell, response)
            if item:
                if item.get('file_urls'):
                    # PDF encontrado na listagem, yield diretamente
                    yield item
                else:
                    # PDF não encontrado, buscar na página de detalhes
                    if item.get('url'):
                        yield scrapy.Request(
                            url=item['url'],
                            callback=self.parse_process_page,
                            meta={'item': item}
                        )

        # Verificar limite de páginas
        current_page = response.meta.get('page_number', 1)
        if self.max_pages and current_page >= self.max_pages:
            self.logger.info(f"Limite de páginas atingido ({self.max_pages}) para {response.url}")
            return

        next_page_link = response.css('a:contains("Próxima")::attr(href)').get()
        if next_page_link:
            self.logger.info(f"Encontrada próxima página: {next_page_link}")
            next_page_url = response.urljoin(next_page_link)
            yield scrapy.Request(next_page_url, callback=self.parse, meta={'page_number': current_page + 1})
        else:
            self.logger.info(f"Fim da paginação para a URL: {response.url}")

    def extract_metadata_from_cell(self, cell_selector, response):
        """Extrai metadados da célula da tabela."""
        item = ProposicaoItem()

        # Get the full text of the cell
        cell_text = ''.join(cell_selector.css('::text').getall()).strip()

        # Find the link (title)
        links = cell_selector.css('a')
        link = links[0] if links else None
        if not link:
            return None

        link_text = link.css('::text').get('').strip()
        link_href = link.css('::attr(href)').get('')

        # Regex para extrair tipo, número, ano e título
        match_titulo = re.search(r'(.+?)\s+(\d+)/(\d{4})\s+-\s+(.*)', link_text)
        if match_titulo:
            item['number'] = str(match_titulo.group(2))  # Manter como string para consistência
            item['year'] = str(match_titulo.group(3))
            item['type'] = match_titulo.group(4).strip()
            item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
        else:
            item['title'] = link_text
            item['number'] = None
            item['year'] = None
            item['type'] = None

        # Extract ementa
        ementa_match = re.search(r'Ementa:\s*(.*?)(?=Apresentação:|Autor:|Texto Original|$)', cell_text, re.DOTALL)
        item['subject'] = ementa_match.group(1).strip() if ementa_match else ''

        # Extract apresentação
        apresentacao_match = re.search(r'Apresentação:\s*(.*?)(?=Processo:|Autor:|Texto Original|$)', cell_text, re.DOTALL)
        item['presentation_date'] = apresentacao_match.group(1).strip() if apresentacao_match else ''

        # Extract autor
        autor_match = re.search(r'Autor:\s*(.*?)(?=Relatorias:|Texto Original|$)', cell_text, re.DOTALL)
        autor = autor_match.group(1).strip() if autor_match else ''
        item['author'] = [autor] if autor else []

        # PDF link - find the "Texto Original" link
        pdf_link = cell_selector.css('a:contains("Texto Original")::attr(href)').get()
        if pdf_link:
            item['url'] = response.urljoin(pdf_link)
            item['file_urls'] = [item['url']]

        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(response.urljoin(link_href).encode('utf-8')).hexdigest()
        item['project_url'] = response.urljoin(link_href)  # URL da página de detalhes do projeto

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item