from .base_sapl import BaseSaplSpider

class CeFortalezaSpider(BaseSaplSpider):
    """
    Coleta proposições da Câmara Municipal de Fortaleza usando SAPL.
    """
    name = 'ce-fortaleza'
    house = 'Câmara Municipal de Fortaleza'
    uf = 'CE'
    slug = 'ce-fortaleza'
    domain = 'sapl.fortaleza.ce.leg.br'
    base_url = "https://sapl.fortaleza.ce.leg.br/materia/pesquisar-materia"

    # Tipos de documento específicos para Fortaleza
    TIPOS_DOCUMENTO = {
        1: "Projeto de Lei Ordinária",
        5: "Projeto de Lei Complementar",
        6: "Projeto de Decreto Legislativo",
        9: "Projeto de Emenda à Lei Orgânica",
    }



