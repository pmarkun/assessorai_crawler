import re
from datetime import datetime
import hashlib
from .base_sapl import BaseSaplSpider
from ..items import ProposicaoItem

class MgContagemSpider(BaseSaplSpider):
    """
    Coleta proposições da Câmara Municipal de Contagem usando SAPL.
    # Gerado via AI
    """
    name = 'mg-contagem'
    house = 'Câmara Municipal de Contagem'
    uf = 'MG'
    slug = 'mg-contagem'
    domain = 'legislativo.cmc.mg.gov.br:8080'
    base_url = "http://legislativo.cmc.mg.gov.br:8080/sapl/generico/materia_pesquisar_form"

    # Tipos de documento para Contagem
    TIPOS_DOCUMENTO = {
        'PLL': "Projeto de Lei do Poder Legislativo",
        'PLCL': "Projeto de Lei Complementar do Poder Legislativo",
        'PR': "Projeto de Resolução",
        'PLIP': "Projeto de Lei de Iniciativa Popular",
        'PLE': "Projeto de Lei do Poder Executivo",
        'PLCE': "Projeto de Lei Complementar do Poder Executivo",
        'REQ': "Requerimento",
        'IND': "Indicação",
        'MOC': "Moção",
    }
    default_tipo = 'PLL'

    def parse(self, response):
        """Processa a página de listagem, extrai os itens e segue para a próxima página."""
        self.logger.info(f"Processando página de listagem: {response.url}")

        linhas = response.css('table.table-striped tr')
        self.logger.info(f"Encontradas {len(linhas)} matérias para processar nesta página.")

        for linha in linhas:
            item = self.extract_metadata_from_row(linha, response)
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

        next_page_link = response.css('a.page-link:contains("Próxima")::attr(href)').get()
        if next_page_link:
            self.logger.info(f"Encontrada próxima página: {next_page_link}")
            next_page_url = response.urljoin(next_page_link)
            yield scrapy.Request(next_page_url, callback=self.parse, meta={'page_number': current_page + 1})
        else:
            self.logger.info(f"Fim da paginação para a URL: {response.url}")

    def extract_metadata_from_row(self, linha_selector, response):
        """Extrai metadados da linha da tabela."""
        item = ProposicaoItem()
        link_titulo_tag = linha_selector.css('a')
        if not link_titulo_tag:
            return None

        texto_titulo_completo = link_titulo_tag.css('::text').get('').strip()
        link_detalhes_relativo = link_titulo_tag.css('::attr(href)').get('')

        # Regex para extrair tipo, número, ano e título
        match_titulo = re.search(r'(\w+)\s+(\d+)/(\d{4})\s+-\s+(.*)', texto_titulo_completo)
        if match_titulo:
            item['number'] = str(match_titulo.group(2))  # Manter como string para consistência
            item['year'] = str(match_titulo.group(3))
            item['type'] = match_titulo.group(4).strip()
            item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
        else:
            item['title'] = texto_titulo_completo
            item['number'] = None
            item['year'] = None
            item['type'] = None

        item['subject'] = linha_selector.css('div.dont-break-out::text').get('').strip()
        item['presentation_date'] = linha_selector.xpath("string(.//strong[contains(text(), 'Apresentação:')]/following-sibling::text()[1])").get('').strip()
        item['author'] = [linha_selector.xpath("string(.//strong[contains(text(), 'Autor:')]/following-sibling::text()[1])").get('').strip()]

        pdf_relative_url = linha_selector.css('a:contains("Texto Original")::attr(href)').get()
        if pdf_relative_url:
            item['url'] = response.urljoin(pdf_relative_url)
            item['file_urls'] = [item['url']]

        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(response.urljoin(link_detalhes_relativo).encode('utf-8')).hexdigest()
        item['project_url'] = response.urljoin(link_detalhes_relativo)  # URL da página de detalhes do projeto

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item