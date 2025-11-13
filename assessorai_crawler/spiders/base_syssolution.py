# assessorai_crawler/spiders/base_syssolution.py

import scrapy
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem

class BaseSyssolutionSpider(scrapy.Spider):
    """Classe base para spiders do sistema 'SysSolution' (usado em várias câmaras)."""

    # Atributos a serem definidos nas subclasses
    uf = None
    slug = None
    house = None
    domain = None
    base_url = None  # Ex.: "https://cmcurvelo.mg.gov.br/Projetos"

    # Tipos de documento suportados
    TIPOS_DOCUMENTO = {
        "Projeto de Lei": "Projeto de Lei",
        "Projeto de Lei Complementar": "Projeto de Lei Complementar",
        "Projeto de Emenda a Lei Organica": "Projeto de Emenda a Lei Organica",
        "Projeto de Resolução": "Projeto de Resolução",
        "Emenda": "Emenda",
        "Projeto de Decreto Legislativo": "Projeto de Decreto Legislativo",
        "Veto": "Veto",
    }

    # Configurações padrão
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DOWNLOAD_DELAY': 1,
    }

    def __init__(self, ano=None, tipo=None, max_pages=None, reset=None, test_mode=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ano = ano
        self.tipo = tipo
        self.max_pages = int(max_pages) if max_pages is not None else None
        self.reset = reset
        self.test_mode = test_mode
        if self.test_mode:
            self.custom_settings.update({
                'CLOSESPIDER_ITEMCOUNT': 5,
                'LOG_LEVEL': 'DEBUG',
            })

        if not self.domain or not self.base_url:
            raise ValueError("Subclass must define 'domain' and 'base_url'")

        self.allowed_domains = [self.domain]

    def start_requests(self):
        """Gera as requisições iniciais para a primeira página."""
        url = f"{self.base_url}/1"
        # Para filtros, pode ser necessário usar FormRequest, mas por simplicidade, começar sem filtros
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """Processa a página de listagem, extrai os itens e segue para a próxima página."""
        self.logger.info(f"Processando página de listagem: {response.url}")

        # Extrair projetos da lista
        projetos = response.css('div.generic-item')  # Ajustar seletor baseado na estrutura
        self.logger.info(f"Encontrados {len(projetos)} projetos para processar nesta página.")

        for projeto in projetos:
            item = self.extract_metadata_from_list(projeto, response)
            if item and item.get('url'):
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

        # Paginação: links como /Projetos/2
        next_page_link = response.css('a:contains("Próxima página")::attr(href)').get()
        if next_page_link:
            self.logger.info(f"Encontrada próxima página: {next_page_link}")
            next_page_url = response.urljoin(next_page_link)
            yield scrapy.Request(next_page_url, callback=self.parse, meta={'page_number': current_page + 1})
        else:
            self.logger.info(f"Fim da paginação para a URL: {response.url}")

    def extract_metadata_from_list(self, projeto_selector, response):
        """Extrai metadados do projeto na lista."""
        item = ProposicaoItem()

        # Título e link
        titulo_tag = projeto_selector.css('h4 a')
        if not titulo_tag:
            return None

        titulo_texto = titulo_tag.css('::text').get('').strip()
        link_detalhes = titulo_tag.css('::attr(href)').get()

        # Extrair tipo, número, ano
        match = re.search(r'(PL)\s+(\d+)/(\d{4})', titulo_texto)
        if match:
            item['type'] = 'Projeto de Lei'
            item['number'] = match.group(2)
            item['year'] = match.group(3)
            item['title'] = titulo_texto
        else:
            item['title'] = titulo_texto

        # Assunto
        assunto = projeto_selector.css('p::text').get('').strip()
        item['subject'] = assunto

        # Autor
        autor_texto = projeto_selector.xpath(".//span[contains(text(), 'Autor:')]/following-sibling::text()").get('').strip()
        item['author'] = [autor_texto] if autor_texto else []

        # Data
        data_texto = projeto_selector.xpath(".//span[contains(text(), 'Data:')]/following-sibling::text()").get('').strip()
        item['presentation_date'] = data_texto

        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(response.urljoin(link_detalhes).encode('utf-8')).hexdigest()
        item['url'] = response.urljoin(link_detalhes)  # URL de detalhes
        item['project_url'] = item['url']

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item

    def parse_process_page(self, response):
        """Processa a página de detalhes para encontrar o PDF."""
        item = response.meta['item']

        # Procurar botão "Baixar PDF"
        pdf_button = response.css('button:contains("Baixar PDF")')
        if pdf_button:
            # Simular clique ou encontrar URL
            # Como é JavaScript, pode ser necessário usar selenium ou analisar o código
            # Por simplicidade, assumir que há um link
            pdf_url = response.css('a[href*=".pdf"]::attr(href)').get()
            if pdf_url:
                item['file_urls'] = [response.urljoin(pdf_url)]

        if not item.get('file_urls'):
            self.logger.warning(f"PDF não encontrado para '{item['title']}'")

        yield item 

