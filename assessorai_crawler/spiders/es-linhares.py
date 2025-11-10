# assessorai_crawler/spiders/es-linhares.py

from .base_camarasempapel import BaseCamarasempapelSpider

class EsLinharesSpider(BaseCamarasempapelSpider):
    """Coleta proposições da Câmara Municipal de Linhares."""
    name = 'es-linhares'
    house = 'Câmara Municipal de Linhares'
    uf = 'ES'
    slug = 'es-linhares'
    domain = 'linhares.camarasempapel.com.br'

    # Override custom_settings to add USER_AGENT
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_TIMES': 3,
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }



