# assessorai_crawler/spiders/sp-sao-jose-dos-campos.py

from .base_camarasempapel import BaseCamarasempapelSpider

class SpSaoJoseDosCamposSpider(BaseCamarasempapelSpider):
    """Coleta proposições da Câmara Municipal de São José dos Campos."""
    name = 'sp-sao-jose-dos-campos'
    house = 'Câmara Municipal de São José dos Campos'
    uf = 'SP'
    slug = 'sp-sao-jose-dos-campos'
    domain = 'camarasempapel.camarasjc.sp.gov.br'
    default_tipo = 348
    extra_params = ["procuraTexto=DocumentoInicial"]

    # Override custom_settings for higher concurrency
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'RETRY_TIMES': 3,
        'ROBOTSTXT_OBEY': False,
    }



