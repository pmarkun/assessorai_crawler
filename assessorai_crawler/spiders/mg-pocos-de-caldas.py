from .base_siscam import BaseSiscamSpider

class MgPocosDeCaldasSpider(BaseSiscamSpider):
    """
    Coleta as proposições da Câmara Municipal de Poços de Caldas de acordo com o dicionario de dados TIPOS_DOCUMENTO
    """
    name = 'mg-pocos-de-caldas'
    house = 'Câmara Municipal de Poços de Caldas'
    uf = 'MG'
    slug = name
    domain = 'pocosdecaldas.siscam.com.br'

    # Dicionário de tipos de documento a serem coletados para Poços de Caldas. Há outros tipos disponíveis no site que não foram coletados.
    tipos_documento = {
        137: "Projeto de Decreto Legislativo",
        139: "Projeto de Emenda à Lei Orgânica",
        135: "Projeto de Lei",
        136: "Projeto de Lei Complementar",
    }
    
