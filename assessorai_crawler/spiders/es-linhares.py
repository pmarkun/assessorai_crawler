# assessorai_crawler/spiders/es-linhares.py

from .base_camarasempapel import BaseCamarasempapelSpider

class EsLinharesSpider(BaseCamarasempapelSpider):
    """Coleta proposições da Câmara Municipal de Linhares."""
    name = 'es-linhares'
    house = 'Câmara Municipal de Linhares'
    uf = 'ES'
    slug = 'es-linhares'
    domain = 'linhares.camarasempapel.com.br'


