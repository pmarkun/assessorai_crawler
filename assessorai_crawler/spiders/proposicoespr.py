from .proposicoeslegislapi import ProposicoesLegislapi
from ..utils import clean_json_text

class ProposicoesPRSpider(ProposicoesLegislapi):
    name = 'proposicoespr'
    house = 'Assembleia Legislativa do Paraná'
    uf = 'pr'
    slug = name.replace(' ', '_').lower()

    def build_url(self, entry, meta):
        url = f'https://consultas.assembleia.pr.leg.br/#/pesquisa-legislativa'
        return url
        