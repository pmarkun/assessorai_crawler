import scrapy
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem

class CeFortalezaSpider(scrapy.Spider):
    """
    Coleta TODAS as proposições da Câmara Municipal de Fortaleza, implementando
    paginação e seguindo a arquitetura do projeto AssessorAI.
    """
    name = 'ce-fortaleza'
    house = 'Câmara Municipal de Fortaleza'
    uf = 'CE'
    slug = 'ce-fortaleza'
    allowed_domains = ['sapl.fortaleza.ce.leg.br']
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DOWNLOAD_DELAY': 1 
    }
    
    TIPOS_DOCUMENTO = {
        #8: "Indicação",
        #10: "Mensagem",
        #12: "Parecer Prévio do Tribunal de Contas",
        6: "Projeto de Decreto Legislativo",
        9: "Projeto de Emenda à Lei Orgânica",
        #13: "Projeto de Iniciativa Popular",
        5: "Projeto de Lei Complementar",
        1: "Projeto de Lei Ordinária",
        #2: "Projeto de Resolução",
        #14: "Protocolo da Casa",
        #4: "Recurso",
        #3: "Requerimento",
        #11: "Veto"
    }

    def start_requests(self):
        """Gera as requisições iniciais para a PRIMEIRA página de cada tipo."""
        base_url = "https://sapl.fortaleza.ce.leg.br/materia/pesquisar-materia"
        self.logger.info(f"Iniciando coleta para os tipos: {list(self.TIPOS_DOCUMENTO.values())}")
        for codigo in self.TIPOS_DOCUMENTO.keys():
            url = f"{base_url}?page=1&tipo={codigo}"
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        """
        Processa a página de listagem, extrai os itens e segue para a próxima página.
        """
        self.logger.info(f"Processando página de listagem: {response.url}")
        
        linhas = response.css('table.table-striped tr')
        self.logger.info(f"Encontradas {len(linhas)} matérias para processar nesta página.")
        
        for linha in linhas:
            item = self.extract_metadata_from_row(linha, response)
            if item:
                yield item
        
        next_page_link = response.css('a.page-link:contains("Próxima")::attr(href)').get()
        if next_page_link:
            self.logger.info(f"Encontrada próxima página: {next_page_link}")
            yield response.follow(next_page_link, callback=self.parse)
        else:
            self.logger.info(f"Fim da paginação para a URL: {response.url}")

    def extract_metadata_from_row(self, linha_selector, response):
        item = ProposicaoItem()
        link_titulo_tag = linha_selector.css('a')
        if not link_titulo_tag: return None
        texto_titulo_completo = link_titulo_tag.css('::text').get('').strip()
        link_detalhes_relativo = link_titulo_tag.css('::attr(href)').get('')
        match_titulo = re.search(r'(\w+)\s+(\d+)/(\d{4})\s+-\s+(.*)', texto_titulo_completo)
        if match_titulo:
            item['number'] = int(match_titulo.group(2))
            item['year'] = int(match_titulo.group(3))
            item['type'] = match_titulo.group(4).strip()
            item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
        else:
            item['title'] = texto_titulo_completo
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

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
        item['caminho_arquivo_texto'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item

