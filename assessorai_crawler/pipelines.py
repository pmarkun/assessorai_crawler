import json
import os
from scrapy.exceptions import DropItem

class JsonWriterPipeline:
    def open_spider(self, spider):
        self.output_dir = f'output/{spider.slug}'
        os.makedirs(self.output_dir, exist_ok=True)

    def process_item(self, item, spider):
        filename = f"{item['uuid']}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(dict(item), f, ensure_ascii=False, indent=2)
        return item

class JsonWriterSinglePipeline:
    def open_spider(self, spider):
        # Inicializa a lista de itens
        self.items = []
        # Garante pasta de saída
        output_dir = f'output'
        os.makedirs(output_dir, exist_ok=True)
        self.file_path = os.path.join(output_dir, f'{spider.slug}_proposicoes.json')

    def process_item(self, item, spider):
        # Coleta cada item para depois gravar em lote
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        # Grava todos os itens em um único JSON
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

class ValidationPipeline:
    """Valida itens antes de enviá-los ao pipeline de escrita"""
    def process_item(self, item, spider):
        # Verifica se o item implementa validação
        missing = []
        if hasattr(item, 'missing_fields'):
            missing = item.missing_fields()
        if missing:
            spider.logger.warning(
                f"Descartando item incompleto no pipeline (uuid={item.get('uuid')}), faltam: {missing}"
            )
            raise DropItem(f"Campos faltando: {missing}")
        return item