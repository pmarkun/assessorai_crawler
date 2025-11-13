# assessorai_crawler/spiders/mg-curvelo.py

import scrapy

import re

from datetime import datetime

import hashlib

from ..items import ProposicaoItem

from .base_syssolution import BaseSyssolutionSpider

class MgCurveloSpider(BaseSyssolutionSpider):

    name = 'mg-curvelo'

    uf = 'mg'

    slug = 'curvelo'

    house = 'Câmara Municipal de Curvelo'

    domain = 'cmcurvelo.mg.gov.br'

    base_url = 'https://cmcurvelo.mg.gov.br/Projetos'

    api_entity_id = 9  # ID da entidade Curvelo na API

    custom_settings = {
        'ROBOTSTXT_OBEY': False,
    }

    def __init__(self, ano=None, tipo=None, max_pages=None, reset=None, test_mode=None, *args, **kwargs):

        super().__init__(ano=ano, tipo=tipo or "Projeto de Lei", max_pages=max_pages, reset=reset, test_mode=test_mode, *args, **kwargs)
        self.allowed_domains.append('api.syssolution.com.br')

    def start_requests(self):
        """Gera as requisições iniciais para a primeira página."""
        url = f"{self.base_url}/1"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):

        projetos = response.css('div.project-card')

        for projeto_selector in projetos:

            item = self.extract_metadata_from_list(projeto_selector, response)

            if item and item.get('url'):

                yield scrapy.Request(

                    url=item['url'],

                    callback=self.parse_process_page,

                    meta={'item': item}

                )

        # paginação

        current_page = response.meta.get('page_number', 1)

        if self.max_pages and current_page >= self.max_pages:

            return

        next_link = response.css('a:contains("Próxima página")::attr(href)').get()

        if next_link:

            next_url = response.urljoin(next_link)

            yield scrapy.Request(next_url, callback=self.parse, meta={'page_number': current_page + 1})

    def extract_metadata_from_list(self, projeto_selector, response):

        item = ProposicaoItem()

        # Título

        titulo = projeto_selector.css('h4::text').get('').strip()

        if not titulo:

            return None

        item['title'] = titulo

        # Extrair tipo, numero/ano

        match = re.search(r'(.*?) (\d+)/(\d{4})', titulo)

        if match:

            item['type'] = match.group(1)

            item['number'] = match.group(2)

            item['year'] = match.group(3)

        # Assunto

        assunto = projeto_selector.css('p::text').get('').strip()

        item['subject'] = assunto

        # Autor

        autor = projeto_selector.xpath(".//span[contains(text(), 'Autor:')]/following-sibling::span/text()").get('').strip()

        item['author'] = [autor] if autor else []

        # Data

        data = projeto_selector.xpath(".//div[@class='pt-4 border-t border-gray-100']//div[@class='flex justify-between items-center text-sm mb-2']//span[@class='text-gray-500'][2]/text()").get('').strip()

        item['presentation_date'] = data

        # Link detalhes

        link = projeto_selector.css('a:contains("Ver detalhes")::attr(href)').get()

        if link:

            item['url'] = response.urljoin(link)

            item['project_url'] = item['url']

            item['uuid'] = hashlib.md5(item['url'].encode('utf-8')).hexdigest()

        item['house'] = self.house

        item['scraped_at'] = datetime.now().isoformat()

        # md_files

        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'

        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item

    def parse_process_page(self, response):

        item = response.meta['item']

        # Procurar link para PDF

        pdf_url = response.css('a[href*=".pdf"]::attr(href)').get()

        if pdf_url:

            item['file_urls'] = [response.urljoin(pdf_url)]

        else:

            self.logger.warning(f"PDF não encontrado para '{item['title']}'")

        yield item

# Gerado via AI