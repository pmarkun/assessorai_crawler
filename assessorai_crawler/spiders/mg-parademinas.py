# assessorai_crawler/spiders/mg-parademinas.py

import scrapy
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem
from .base_sapl import BaseSaplSpider

class MgParademinasSpider(BaseSaplSpider):
    """
    Coleta proposições da Câmara Municipal de Pará de Minas usando SAPL.
    """
    name = 'mg-parademinas'
    house = 'Câmara Municipal de Pará de Minas'
    uf = 'MG'
    slug = 'mg-parademinas'
    domain = 'sapl.parademinas.mg.leg.br'
    base_url = "https://sapl.parademinas.mg.leg.br/materia/pesquisar-materia"

    # Tipos de documento específicos para Pará de Minas
    TIPOS_DOCUMENTO = {
        1: "Projeto de Lei Ordinária",
    }
    default_tipo = 1

    def parse(self, response):
        """Processa a página de listagem, extrai os itens e segue para a próxima página."""
        self.logger.info(f"Processando página de listagem: {response.url}")

        # Para Pará de Minas, os resultados são em links de matérias, filtrar apenas os que têm texto numérico
        all_links = response.css('a[href*="/materia/"]')
        materia_links = [link for link in all_links if link.css('::text').get('').strip().isdigit()]
        self.logger.info(f"Encontradas {len(materia_links)} matérias para processar nesta página.")

        for link in materia_links:
            item = self.extract_metadata_from_link(link, response)
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

    def extract_metadata_from_link(self, link_selector, response):
        """Extrai metadados do link da matéria."""
        item = ProposicaoItem()

        link_text = link_selector.css('::text').get('').strip()
        link_href = link_selector.css('::attr(href)').get('')

        # Como filtramos para links com texto numérico, link_text é o número
        item['number'] = link_text
        item['year'] = str(self.ano) if self.ano else None
        item['type'] = self.TIPOS_DOCUMENTO.get(self.tipo, 'Unknown')
        item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"

        # Assumir que o link está dentro de um elemento pai que contém toda a informação da matéria
        parent = link_selector.xpath('..')
        materia_text = parent.xpath('string(.)').get('').strip()

        # PDF link - "Texto Original"
        pdf_link = parent.css('a:contains("Texto Original")::attr(href)').get()
        if pdf_link:
            item['url'] = response.urljoin(pdf_link)
            item['file_urls'] = [item['url']]

        # Extrair ementa
        ementa_match = re.search(r'Ementa:\s*(.*?)(?=Apresentação:|$)', materia_text, re.DOTALL)
        item['subject'] = ementa_match.group(1).strip() if ementa_match else ''

        # Apresentação
        apresentacao_match = re.search(r'Apresentação:\s*(.*?)(?=Protocolo:|$)', materia_text, re.DOTALL)
        item['presentation_date'] = apresentacao_match.group(1).strip() if apresentacao_match else ''

        # Autor
        autor_match = re.search(r'Autor:\s*(.*?)(?=Resultado|Localização|Status|$)', materia_text, re.DOTALL)
        autor = autor_match.group(1).strip() if autor_match else ''
        autor = re.sub(r'\s+', ' ', autor).strip()  # Remove extra whitespace
        item['author'] = [autor] if autor else []

        link_url = response.urljoin(link_href)
        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(link_url.encode('utf-8')).hexdigest()
        item['project_url'] = link_url  # URL da página de detalhes do projeto

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item

# Gerado via AI