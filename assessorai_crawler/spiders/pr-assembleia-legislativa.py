from .base_legislapi import ProposicoesLegislapi
from ..utils import clean_json_text

class PrAssembleiaLegislativaSpider(ProposicoesLegislapi):
    name = 'pr-assembleia-legislativa'
    house = 'Assembleia Legislativa do Paraná'
    uf = 'pr'
    slug = name

    def build_url(self, entry, meta):
        url = f'https://consultas.assembleia.pr.leg.br/#/pesquisa-legislativa'
        return url
        