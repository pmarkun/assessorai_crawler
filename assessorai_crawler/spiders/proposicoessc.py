from .proposicoeslegislapi import ProposicoesLegislapi
from ..utils import clean_json_text
import hashlib
import scrapy

class ProposicoesSCSpider(ProposicoesLegislapi):
    name = 'proposicoessc'
    house = 'Assembleia Legislativa de Santa Catarina'
    uf = 'sc'
    slug = name.replace(' ', '_').lower()

    def parse_metadata(self, response):
        self.metadata = {}
        data = clean_json_text(response.text)
        for entry in data:
            key = hashlib.md5(entry['Titulo'].encode('utf-8')).hexdigest()
            alt_titulo = entry.get('Titulo', '').replace("/", " ").strip()
            alt_key = hashlib.md5(alt_titulo.encode('utf-8')).hexdigest()

            self.metadata[key] = entry
            self.metadata[alt_key] = entry #hackish
        yield scrapy.Request(f'file://{self.get_text_file()}', callback=self.parse)

    def build_url(self, entry, meta):
        numero = meta.get('Numero', '')
        ano = meta.get('Ano', '')
        if numero and ano:
            url = f'https://portalelegis.alesc.sc.gov.br/proposicoes/processo-legislativo?search=&numeroPropositura={numero}/{ano}'
            return url
        return ''