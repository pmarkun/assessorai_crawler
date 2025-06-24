from .proposicoeslegislapi import ProposicoesLegislapi

class ProposicoesSPSpider(ProposicoesLegislapi):
    name = 'proposicoessp'
    house = 'Assembleia Legislativa de São Paulo'
    uf = 'sp'
    slug = name.replace(' ', '_').lower()