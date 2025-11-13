# assessorai_crawler/spiders/go-formosa.py

import re
from .base_sapl import BaseSaplSpider

class GoFormosaSpider(BaseSaplSpider):
    """Spider para Câmara Municipal de Formosa, GO."""

    name = 'go-formosa'
    uf = 'GO'
    slug = 'go-formosa'
    house = 'Câmara Municipal de Formosa'
    domain = 'sapl.formosa.go.leg.br'
    base_url = 'https://sapl.formosa.go.leg.br/materia/pesquisar-materia'

    # Tipo padrão para Projeto de Lei Ordinária
    default_tipo = 18

    # Tipos de documento específicos para Formosa
    TIPOS_DOCUMENTO = {
        18: "Projeto de Lei Ordinária",
    }

    def extract_metadata_from_row(self, linha_selector, response):
        """Extrai metadados da linha da tabela, adaptado para Formosa."""
        item = super().extract_metadata_from_row(linha_selector, response)
        if not item:
            return None

        # Ajustar o type para o formato usado em Formosa (ex: PLOPL)
        texto_titulo_completo = linha_selector.css('a::text').get('').strip()
        match_titulo = re.search(r'(\w+)\s+(\d+)/(\d{4})', texto_titulo_completo)
        if match_titulo:
            item['type'] = match_titulo.group(1)
            item['number'] = str(match_titulo.group(2))
            item['year'] = str(match_titulo.group(3))
            item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
            # Ajustar md_files para usar o type correto
            normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a')
            item['md_files'] = f"{self.uf}/{self.slug}/{normalized_type}-{item['number']}-{item['year']}.md"

        return item