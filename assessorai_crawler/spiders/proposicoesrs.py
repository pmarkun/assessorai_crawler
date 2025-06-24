from .proposicoeslegislapi import ProposicoesLegislapi
from ..utils import clean_json_text

#METADATA BROKEN

class ProposicoesRSSpider(ProposicoesLegislapi):
    name = 'proposicoesrs'
    house = 'Assembleia Legislativa do Rio Grande do Sul'
    uf = 'rs'
    slug = name.replace(' ', '_').lower()

    def build_url(self, entry, meta):
        raw_title = entry.get('Titulo', '').strip()
        tipo = raw_title.split()[0].upper()
        numero = raw_title.split()[1].split("/")[0].strip()
        ano = raw_title.split()[1].split("/")[1].strip() if '/' in raw_title.split()[1] else ''
        if tipo and numero and ano: 
            url = f'https://ww4.al.rs.gov.br/legislativo/pesquisa?siglaTipoProposicao={tipo}&nroProposicao={numero}&anoProposicao={ano}'
            return url
        return ''
            