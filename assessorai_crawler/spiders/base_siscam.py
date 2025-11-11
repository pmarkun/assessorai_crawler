# assessorai_crawler/spiders/base_siscam.py

import scrapy
import re
from datetime import datetime
import hashlib
from ..items import ProposicaoItem

class BaseSiscamSpider(scrapy.Spider):
    """Classe base para spiders do sistema 'siscam' (usado em várias câmaras)."""

    # Atributos a serem definidos nas subclasses
    uf = None
    slug = None
    house = None
    domain = None
    tipos_documento = {}  # Dicionário de tipos

    # Configurações padrão
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'ROBOTSTXT_OBEY': False
    }

    def __init__(self, ano=None, max_pages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ano = ano
        self.max_pages = int(max_pages) if max_pages is not None else None

        if not self.domain:
            raise ValueError("Subclass must define 'domain'")

        self.allowed_domains = [self.domain]

    def start_requests(self):
        """
        Gera as requisições iniciais para a PRIMEIRA página de cada tipo de documento.
        """
        base_url = f"https://{self.domain}/Documentos/Pesquisa"
        self.logger.info(f"Iniciando coleta para os tipos: {list(self.tipos_documento.values())}")

        for codigo_tipo in self.tipos_documento.keys():
            url = f"{base_url}?Pesquisa=Avancada&id=80&pagina=1&Modulo=8&Documento={codigo_tipo}&Numeracao=Documento&NumeroInicial=&AnoInicial={self.ano or ''}&DataInicial=&NumeroFinal=&AnoFinal=&DataFinal=&SubTipoId=0&Situacao=0&TipoAutor=Todos&AutoriaId=0&Iniciativa=Nenhum&NoTexto=false&Assunto=&Observacoes="
            yield scrapy.Request(
                url,
                callback=self.parse,
                # Passamos o 'codigo_tipo' e 'page_number' para controlar a paginação
                meta={'page_number': 1, 'codigo_tipo': codigo_tipo}
            )

    def parse(self, response):
        """
        Processa a página de listagem, extrai os itens e segue para a próxima página.
        """
        page_number = response.meta['page_number']
        codigo_tipo = response.meta['codigo_tipo']
        self.logger.info(f"Processando página {page_number} para o tipo de documento {codigo_tipo}.")

        proposicoes = response.css("div.data-list-item")
        self.logger.info(f"Encontradas {len(proposicoes)} matérias para processar nesta página.")

        # Se a página não retornar itens, consideramos o fim da paginação para este tipo.
        if not proposicoes:
            self.logger.info(f"Nenhuma proposição encontrada na página {page_number}. Fim da paginação para o tipo {codigo_tipo}.")
            return

        for proposicao_selector in proposicoes:
            item = self.extract_metadata(proposicao_selector, response)
            if item:
                yield item

        # Lógica de paginação: constrói a URL da próxima página e continua a coleta.
        if self.max_pages and page_number >= self.max_pages:
            self.logger.info(f"Limite de páginas atingido ({self.max_pages}) para {response.url}")
            return

        next_page = page_number + 1
        next_page_url = response.urljoin(f"?Pesquisa=Avancada&id=80&pagina={next_page}&Modulo=8&Documento={codigo_tipo}&Numeracao=Documento&NumeroInicial=&AnoInicial={self.ano or ''}&DataInicial=&NumeroFinal=&AnoFinal=&DataFinal=&SubTipoId=0&Situacao=0&TipoAutor=Todos&AutoriaId=0&Iniciativa=Nenhum&NoTexto=false&Assunto=&Observacoes=")

        self.logger.info(f"Agendando próxima página: {next_page_url}")
        yield scrapy.Request(
            next_page_url,
            callback=self.parse,
            meta={'page_number': next_page, 'codigo_tipo': codigo_tipo}
        )

    def extract_metadata(self, proposicao_selector, response):
        """
        Extrai os metadados de uma única proposição na página de listagem.
        """
        item = ProposicaoItem()

        title_tag = proposicao_selector.css("h4 a")
        if not title_tag:
            return None

        full_title_text = title_tag.css('::text').get('').strip()
        link_detalhes_relativo = title_tag.css('::attr(href)').get('')

        match = re.search(r'^(.*?)\s+Nº\s+(\d+)/(\d{4})', full_title_text, re.IGNORECASE)
        if match:
            item['type'] = match.group(1).strip()
            item['number'] = int(match.group(2))
            item['year'] = int(match.group(3))
            item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
        else:
            item['title'] = full_title_text

        def get_text_from_p_tag(strong_text):
            """
            Função auxiliar para extrair texto de uma tag <p> que contém uma <strong> específica.
            Ex: <p><strong>Assunto:</strong> Este é o assunto.</p> -> Retorna: "Este é o assunto."
            """
            p_tag_text = proposicao_selector.xpath(f".//p[strong[contains(text(), '{strong_text}')]]//text()").getall()
            if not p_tag_text:
                return None

            full_text = " ".join(p.strip() for p in p_tag_text).strip()
            label_to_remove = f"{strong_text.strip()} "
            cleaned_text = full_text.replace(label_to_remove, "").strip()
            return cleaned_text

        autores_texto = get_text_from_p_tag("Autoria:")
        item['author'] = [autor.strip() for autor in autores_texto.split(',')] if autores_texto else []
        item['subject'] = get_text_from_p_tag("Assunto:")
        item['presentation_date'] = get_text_from_p_tag("Data:")

        pdf_link_tag = proposicao_selector.css('a[title="Documento Assinado"]::attr(href)').get()
        if not pdf_link_tag:
            pdf_link_tag = proposicao_selector.css('a[href*="/arquivo?Id="]::attr(href)').get()

        if pdf_link_tag:
            item['url'] = response.urljoin(pdf_link_tag)
            item['file_urls'] = [item['url']]

        item['house'] = self.house
        item['scraped_at'] = datetime.now().isoformat()
        item['uuid'] = hashlib.md5(response.urljoin(link_detalhes_relativo).encode('utf-8')).hexdigest()

        # Caminho para .md
        normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a').replace('ê', 'e') if item['type'] else 'unknown'
        item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item