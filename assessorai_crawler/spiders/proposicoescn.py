import scrapy
import json
import hashlib
from datetime import datetime
from ..items import ProposicaoItem

import urllib.parse
class ProposicoesCNSpider(scrapy.Spider):
    name = 'proposicoescn'
    slug = name.replace(' ', '_').lower()
    slug = slug.encode('ascii', 'ignore').decode('ascii')

    # Read local JSON file
    start_urls = ['file:///home/markun/devel/datasets/legisla/cn/ProposicaoComEmentas.json']

    def parse(self, response):
        data = json.loads(response.text)
        for entry in data:
            item = ProposicaoItem()
            raw_title = entry.get('Titulo', '')
            item['title'] = raw_title.strip()

            # Parse type, number, year from title
            parts = raw_title.split()
            item['type'] = parts[0] if parts else ''
            num_year = parts[1] if len(parts) > 1 else ''
            if '/' in num_year:
                num, yr = num_year.split('/')
                try:
                    item['number'] = int(num)
                    item['year'] = int(yr)
                except ValueError:
                    item['number'] = None
                    item['year'] = None
            else:
                item['number'] = None
                item['year'] = None

            # Other fields
            item['house'] = "Câmara dos Deputados"
            authors = entry.get('Autoria', '')
            item['author'] = [a.strip() for a in authors.split(',')] if authors else []
            item['subject'] = entry.get('ementa', '')
            item['full_text'] = entry.get('Texto', '')
            item['presentation_date'] =  f"{item['year']}-01-01" if item['year'] else None
            item['length'] = len(item['full_text'] or '')
            #item['chunks'] = self.chunk_text(item['full_text'] or '')

            # Encode filters for URL
            filters = json.dumps([
                {"numero": str(item['number'])},
                {"ano": str(item['year'])}
            ])
            encoded_filters = urllib.parse.quote(filters)
            item['url'] = f'https://www.camara.leg.br/busca-portal?contextoBusca=BuscaProposicoes&filtros={encoded_filters}&tipos={item["type"]}&pagina=1'

            # UUID based on house_type_number_year
            uid_src = f"{item['house']}_{item['type']}_{item['number']}_{item['year']}"
            item['uuid'] = hashlib.md5(uid_src.encode('utf-8')).hexdigest()
            item['scraped_at'] = datetime.utcnow().date().isoformat()

            yield item

    def chunk_text(self, text, max_tokens=5000, overlap_tokens=50):
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + max_tokens, len(words))
            chunks.append(' '.join(words[start:end]))
            start = end - overlap_tokens if end < len(words) else len(words)
        return chunks
