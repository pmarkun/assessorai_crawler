from .proposicoeslegislapi import ProposicoesLegislapi

class SpAssembleiaLegislativaSpider(ProposicoesLegislapi):
    name = 'sp-assembleia-legislativa'
    house = 'Assembleia Legislativa de São Paulo'
    uf = 'sp'
    slug = name