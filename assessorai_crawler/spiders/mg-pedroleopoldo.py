# assessorai_crawler/spiders/mg-pedroleopoldo.py

import scrapy
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem
from .base_sapl import BaseSaplSpider

class MgPedroleopoldoSpider(BaseSaplSpider):
    """
    Coleta proposições da Câmara Municipal de Pedro Leopoldo usando SAPL.
    """
    name = 'mg-pedroleopoldo'
    house = 'Câmara Municipal de Pedro Leopoldo'
    uf = 'MG'
    slug = 'pedroleopoldo'
    domain = 'sapl.pedroleopoldo.mg.leg.br'
    base_url = "https://sapl.pedroleopoldo.mg.leg.br/materia/pesquisar-materia"

    # Tipos de documento específicos para Pedro Leopoldo
    TIPOS_DOCUMENTO = {
        1: "Projeto de Lei Ordinária",
    }
    default_tipo = 1

    def parse(self, response):
        """Processa a página de listagem, extrai os itens e segue para a próxima página."""
        self.logger.info(f"Processando página de listagem: {response.url}")

        # Para Pedro Leopoldo, os resultados são em links de matérias
        all_links = response.css('a[href*="/materia/"]')
        materia_links = [link for link in all_links if 'PLO' in link.css('::text').get('')]
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

        # Regex para extrair tipo, número, ano e título
        match_titulo = re.search(r'PLO\s+(\d+)/(\d{4})\s+-\s+(.+)', link_text)
        if match_titulo:
            item['number'] = str(match_titulo.group(1))  # Manter como string para consistência
            item['year'] = str(match_titulo.group(2))
            item['type'] = match_titulo.group(3).strip()
            item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
        else:
            item['title'] = link_text
            item['number'] = None
            item['year'] = None
            item['type'] = None

        # O link é seguido por parágrafos com ementa, apresentação, etc.
        parent = link_selector.xpath('..')

        # PDF link - "Texto Original" pode estar no mesmo container
        pdf_link = parent.xpath('following-sibling::*//a[contains(text(), "Texto Original")]/@href').get()
        if pdf_link:
            item['url'] = response.urljoin(pdf_link)
            item['file_urls'] = [item['url']]

        link_url = response.urljoin(link_href)
        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(link_url.encode('utf-8')).hexdigest()
        item['project_url'] = link_url  # URL da página de detalhes do projeto

        # Extrair ementa do parágrafo seguinte
        ementa_p = parent.xpath('following-sibling::p[contains(text(), "Ementa:")][1]')
        if ementa_p:
            ementa_text = ementa_p.xpath('string(.)').get('').replace('Ementa:', '').strip()
            item['subject'] = ementa_text
        else:
            item['subject'] = ''

        # Apresentação
        apresentacao_p = parent.xpath('following-sibling::p[contains(text(), "Apresentação:")][1]')
        if apresentacao_p:
            apresentacao_text = apresentacao_p.xpath('string(.)').get('').replace('Apresentação:', '').strip()
            item['presentation_date'] = apresentacao_text
        else:
            item['presentation_date'] = ''

        # Autor
        autor_p = parent.xpath('following-sibling::p[contains(text(), "Autor:")][1]')
        if autor_p:
            autor_text = autor_p.xpath('string(.)').get('').replace('Autor:', '').strip()
            autor = re.sub(r'\s+', ' ', autor_text).strip()
            item['author'] = [autor] if autor else []
        else:
            item['author'] = []

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item

# Gerado via AI