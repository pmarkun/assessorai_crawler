from .base_legislapi import ProposicoesLegislapi
from ..utils import clean_json_text

#METADATA BROKEN

class BaAssembleiaLegislativaSpider(ProposicoesLegislapi):
    name = 'ba-assembleia-legislativa'
    house = 'Assembleia Legislativa da Bahia'
    uf = 'ba'
    slug = name

    def build_url(self, entry, meta):
        raw_title = entry.get('Titulo', '').strip()
        tipo = raw_title.split()[0].upper()
        numero = raw_title.split()[1].split("/")[0].strip()
        ano = raw_title.split()[1].split("/")[1].strip() if '/' in raw_title.split()[1] else ''
        
        if tipo and numero and ano:
            url = f'https://www.al.ba.gov.br/atividade-legislativa-nova/proposicao/{tipo}.-{numero}-{ano}'
            return url
        return ''
        