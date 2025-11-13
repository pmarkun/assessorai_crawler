# assessorai_crawler/spiders/sp-atibaia.py

import scrapy
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem

class SpAtibaiaSpider(scrapy.Spider):
    """Coleta proposições da Câmara Municipal de Atibaia, SP."""

    name = 'sp-atibaia'
    house = 'Câmara Municipal de Atibaia'
    uf = 'SP'
    slug = 'sp-atibaia'
    allowed_domains = ['camaraatibaia.sp.gov.br']
    base_url = "https://www.camaraatibaia.sp.gov.br/"

    # Configurações padrão
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DOWNLOAD_DELAY': 1,
    }

    def __init__(self, ano=None, tipo=10, max_pages=None, reset=None, test_mode=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ano = ano
        self.tipo = tipo  # Default to 10 for Projeto de Lei
        self.max_pages = int(max_pages) if max_pages is not None else None
        self.reset = reset
        self.test_mode = test_mode
        if self.test_mode:
            self.custom_settings.update({
                'CLOSESPIDER_ITEMCOUNT': 5,
                'LOG_LEVEL': 'DEBUG',
            })

    def start_requests(self):
        """Gera a requisição inicial."""
        params = f"pag=T1RFPU9UVT1PVEk9T0dZPU9HRT1PV0k9T1RZPQ==&view=getTPT&tp={self.tipo}&estado=tramitado"
        if self.ano:
            params += f"&ano={self.ano}"
        params += "&pg=1"
        url = f"{self.base_url}?{params}"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """Processa a página de listagem, extrai os itens e segue para a próxima página."""
        self.logger.info(f"Processando página de listagem: {response.url}")

        # Find all project tds
        blocks = response.xpath("//td[.//h4[contains(text(), 'Projeto de Lei Nº')]]")
        self.logger.info(f"Encontrados {len(blocks)} projetos nesta página.")

        for block in blocks:
            item = self.extract_metadata_from_block(block, response)
            if item:
                yield item

        # Verificar limite de páginas
        current_page = response.meta.get('page_number', 1)
        if self.max_pages and current_page >= self.max_pages:
            self.logger.info(f"Limite de páginas atingido ({self.max_pages})")
            return

        # Pagination
        next_page_link = response.css('a:contains("Próxima")')
        if next_page_link:
            href = next_page_link.css('::attr(href)').get()
            if href:
                next_page_url = response.urljoin(href)
                self.logger.info(f"Encontrada próxima página: {next_page_url}")
                yield scrapy.Request(next_page_url, callback=self.parse, meta={'page_number': current_page + 1})
        else:
            self.logger.info("Fim da paginação")

    def extract_metadata_from_block(self, block, response):
        """Extrai metadados do bloco td."""
        item = ProposicaoItem()

        # Extract title
        h4 = block.css('h4')
        if not h4:
            return None
        texto_titulo = h4[0].css('::text').get('').strip()
        match_titulo = re.search(r'Projeto de Lei Nº (\d+)-(\d{4})', texto_titulo)
        if not match_titulo:
            return None
        item['number'] = str(match_titulo.group(1))
        item['year'] = str(match_titulo.group(2))
        item['type'] = 'Projeto de Lei'
        item['title'] = f"Projeto de Lei nº {item['number']}/{item['year']}"

        # Extract data inicial
        data_elem = block.xpath('.//h4[contains(text(), "Data Inicial:")]/following-sibling::text()[1]')
        item['presentation_date'] = data_elem.get('').strip() if data_elem else ''

        # Extract autor
        autor_elem = block.xpath('.//h4[contains(text(), "Autor:")]/following-sibling::text()[1]')
        item['author'] = [autor_elem.get('').strip()] if autor_elem else ['']

        # Extract ementa
        ementa_elem = block.xpath('.//h4[contains(text(), "Ementa:")]/following-sibling::text()[1]')
        item['subject'] = ementa_elem.get('').strip() if ementa_elem else ''

        # Extract project_url
        link_elem = block.css('a')
        project_url = ''
        if link_elem:
            href = link_elem.css('::attr(href)').get()
            if href:
                project_url = response.urljoin(href)
        item['project_url'] = project_url
        item['url'] = project_url  # Required field

        # Extract file_urls from the form
        file_urls = []
        form = block.css('form')
        if form:
            action = form.css('::attr(action)').get()
            inputs = form.css('input')
            params = {}
            for inp in inputs:
                name = inp.css('::attr(name)').get()
                value = inp.css('::attr(value)').get()
                if name and value is not None:
                    params[name] = value
            if action and params:
                query = '&'.join(f"{k}={v}" for k, v in params.items())
                separator = "&" if "?" in action else "?"
                file_url = response.urljoin(action) + separator + query
                file_urls.append(file_url)
        item['file_urls'] = file_urls

        # Set fixed fields
        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(project_url.encode('utf-8')).hexdigest() if project_url else ''

        # md_files
        normalized_type = 'projeto-de-lei'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item