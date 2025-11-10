from .proposicoeslegislapi import ProposicoesLegislapi
from ..utils import clean_json_text

class MgAssembleiaLegislativaSpider(ProposicoesLegislapi):
    name = 'mg-assembleia-legislativa'
    house = 'Assembleia Legislativa de Minas Gerais'
    uf = 'mg'
    slug = name

    def build_url(self, entry, meta):
        tipo = meta.get('Titulo','').split()[0].upper()
        numero = meta.get('Numero', '')
        ano = meta.get('Ano', '')
        if tipo and numero and ano:
            url = f'https://www.almg.gov.br/projetos-de-lei/{tipo}/{numero}/{ano}'
            return url
        return ''