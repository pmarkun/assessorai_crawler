# assessorai_crawler/spiders/sp-sao-jose-dos-campos.py

import scrapy
from urllib.parse import urlparse, parse_qs, urljoin
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem

class SpSaoJoseDosCamposSpider(scrapy.Spider):
    """Coleta proposições da Câmara Municipal de São José dos Campos."""
    name = 'sp-sao-jose-dos-campos'
    house = 'Câmara Municipal de São José dos Campos'
    uf = 'SP'
    slug = 'sp-sao-jose-dos-campos'
    allowed_domains = ['camarasempapel.camarasjc.sp.gov.br']
    start_urls = ["https://camarasempapel.camarasjc.sp.gov.br/spl/consulta-producao.aspx?tipo=348&procuraTexto=DocumentoInicial"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_TIMES': 3,
        'ROBOTSTXT_OBEY': False,
    }

    def parse(self, response):
        """Processa a página de listagem e segue para a próxima."""
        proposicoes = response.css("div.kt-widget5__item")
        
        for prop in proposicoes:
            item = self.extract_metadata_from_list(prop, response)
            if item and item.get('url'):
                yield scrapy.Request(
                    url=item['url'],
                    callback=self.parse_process_page,
                    meta={'item': item}
                )
        
        # Lógica de paginação: clica no botão "Próxima"
        next_page_button = response.css('a#ContentPlaceHolder1_lbNext')
        if next_page_button and next_page_button.attrib.get('href'):
            current_page_number = response.meta.get('page_number', 1)
            next_page_number = current_page_number + 1
            self.logger.info(f"Navegando para a página {next_page_number}...")

            form_data = {
                '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$lbNext',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': response.css('input#__VIEWSTATE::attr(value)').get(),
                '__VIEWSTATEGENERATOR': response.css('input#__VIEWSTATEGENERATOR::attr(value)').get(),
                '__EVENTVALIDATION': response.css('input#__EVENTVALIDATION::attr(value)').get(),
            }

            yield scrapy.FormRequest(
                url=response.url,
                formdata=form_data,
                callback=self.parse,
                meta={'page_number': next_page_number}
            )

    def parse_process_page(self, response):
        """Encontra o link do PDF na página do processo e configura para download via pipeline."""
        item = response.meta['item']
        caminho_pdf = None

        url_final = response.url
        parsed_url = urlparse(url_final)
        query_params = parse_qs(parsed_url.query)

        if 'arquivo' in query_params and query_params['arquivo'][0]:
            caminho_pdf = query_params['arquivo'][0]
        else:
            pdf_links = response.css("ul#processo_arquivos a[href*='.pdf']")
            link_encontrado = None

            for link in pdf_links:
                link_text = link.css("::text").get('').upper()
                if "PL " in link_text or "PROPOSIÇÃO" in link_text:
                    link_encontrado = link.attrib['href']
                    break

            if link_encontrado:
                parsed_link = urlparse(link_encontrado)
                query_params_link = parse_qs(parsed_link.query)
                if 'arquivo' in query_params_link and query_params_link['arquivo'][0]:
                    caminho_pdf = query_params_link['arquivo'][0]

        if caminho_pdf:
            base_pdf_url = "https://camarasempapel.camarasjc.sp.gov.br/"
            url_direta_pdf = urljoin(base_pdf_url, caminho_pdf)
            item['file_urls'] = [url_direta_pdf]
        else:
            self.logger.warning(f"PDF não encontrado para '{item['title']}'")
            item['full_text'] = "[FALHA] PDF não encontrado na página de documentos."
            item['length'] = len(item['full_text'])

        yield item

    def extract_metadata_from_list(self, prop, response):
        """Extrai os metadados da página de listagem."""
        item = ProposicaoItem()
        titulo_tag = prop.css("a.kt-widget5__title")
        if not titulo_tag: return None
        
        item['title'] = titulo_tag.css('::text').get('').strip()
        
        match = re.search(r'^(.*?)\s+n°\s+(\d+)/(\d{4})', item['title'], re.IGNORECASE)
        item['type'], _, item['year'] = (match.groups() if match else (None, None, None))
        
        protocolo_num = prop.xpath(".//span[contains(text(), 'Protocolo N°:')]/following-sibling::a[1]/text()").get()
        if protocolo_num:
            item['number'] = protocolo_num.strip()
        elif match:
            item['number'] = match.group(2)
        else:
            item['number'] = None

        item['subject'] = prop.css("a.kt-widget5__desc::text").get('').strip()
        autor_tag = prop.css("span.kt-font-info a")
        if autor_tag:
            autor_bruto = ''.join(autor_tag.css('::text').getall())
            autor_limpo = re.sub(r'\s+', ' ', autor_bruto).strip()
            item['author'] = [autor_limpo]
        else:
            item['author'] = []
            
        data_tag = prop.css("span.kt-font-info:contains('Data:') + span.kt-font-info")
        item['presentation_date'] = data_tag.css('::text').get('').strip() if data_tag else None
        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        link_detalhes_abs = response.urljoin(titulo_tag.attrib['href'])
        item['uuid'] = hashlib.md5(link_detalhes_abs.encode('utf-8')).hexdigest()
        link_processo_tag = prop.css("a[href*='Digital.aspx']")
        item['url'] = response.urljoin(link_processo_tag.attrib['href']) if link_processo_tag else None

        # Gerar caminho para arquivo .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('º', '') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item

