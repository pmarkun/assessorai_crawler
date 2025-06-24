import scrapy
import json
import hashlib
from datetime import datetime
from ..items import ProposicaoItem
from ..utils import clean_json_text

class ProposicoesLegislapi(scrapy.Spider):
    name = 'proposicoessp'
    house = 'Assembleia Legislativa de São Paulo'
    folder = '/home/markun/devel/datasets/legisla'
    uf = 'sp'
    slug = name.replace(' ', '_').lower().encode('ascii', 'ignore').decode('ascii')
    
    def get_metadata_file(self):
        """Retorna o caminho do arquivo de metadados"""
        return f'{self.folder}/{self.uf}/Proposicoes{self.uf.upper()}.json'
    
    def get_text_file(self):
        """Retorna o caminho do arquivo de texto completo"""
        return f'{self.folder}/{self.uf}/ProjetoInteiroTeor{self.uf.upper()}.json'
    
    def start_requests(self):
        # Carrega metadados primeiro
        yield scrapy.Request(f'file://{self.get_metadata_file()}', callback=self.parse_metadata)

    def build_url(self, entry, meta):
        """Constrói a URL pública da proposição"""
        id_orig = entry.get('IdProposicaoOrigem')
        if id_orig:
            return f'https://www.al.sp.gov.br/propositura/?id={id_orig}'
        return ''
    
    def parse_metadata(self, response):
        self.metadata = {}
        data = clean_json_text(response.text)
        for entry in data:
            key = hashlib.md5(entry['Titulo'].encode('utf-8')).hexdigest()
            self.metadata[key] = entry
        yield scrapy.Request(f'file://{self.get_text_file()}', callback=self.parse)

    def parse(self, response):
        data = clean_json_text(response.text)
        for entry in data:
            item = ProposicaoItem()

            # Título, Casa, Tipo
            raw_title = entry.get('Titulo', '').strip()
            item['title'] = raw_title
            item['house'] = self.house
            item['type'] = raw_title.split()[0] if raw_title else ''

            # Número e Ano
            num_year = raw_title.split()[1] if len(raw_title.split()) > 1 else ''
            try:
                num, yr = num_year.split('/')
                number = int(num)
                year = int(yr)
            except ValueError:
                number = None
                year = None
            item['number'] = number
            item['year'] = year

            # Metadados (autoria, ementa, data)
            item['uuid'] = hashlib.md5(raw_title.encode('utf-8')).hexdigest()
            meta = self.metadata.get(item["uuid"], {})
            authors = meta.get('Autoria', '')
            item['author'] = [a.strip() for a in authors.split(',')] if authors else []
            item['subject'] = meta.get('Ementa', '')
            item['presentation_date'] = meta.get('DataApresentacao')

            # Texto e métricas
            item['full_text'] = entry.get('Texto', '')
            item['length'] = len(item['full_text'] or '')
            item['meta'] = meta

            # URL pública
            item['url'] = self.build_url(entry, meta)

            # UUID e timestamp
            item['scraped_at'] = datetime.now().isoformat()

            yield item
