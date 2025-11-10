import json
import os
from scrapy.exceptions import DropItem
from scrapy.pipelines.files import FilesPipeline
from scrapy import Request
import google.generativeai as genai
from dotenv import load_dotenv
import hashlib
from datetime import datetime

load_dotenv()

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
        output_dir = os.path.join('storage', 'output')
        os.makedirs(output_dir, exist_ok=True)
        self.file_path = os.path.join(output_dir, f'{spider.slug}_proposicoes.json')
        self.batch_size = spider.settings.get('JSON_BATCH_SIZE', 10)

    def process_item(self, item, spider):
        # Coleta cada item
        self.items.append(dict(item))
        # Salva incrementalmente a cada batch_size itens
        if len(self.items) % self.batch_size == 0:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
        return item

    def close_spider(self, spider):
        # Grava todos os itens finais em um único JSON
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


class ProposicaoFilesPipeline(FilesPipeline):
    """Pipeline customizado para baixar arquivos de proposições"""
    
    def get_media_requests(self, item, info):
        """Baixa todos os arquivos listados em file_urls"""
        urls = item.get('file_urls', [])
        for url in urls:
            yield Request(url)
    
    def file_path(self, request, response=None, info=None, *, item=None):
        """Define o caminho onde o arquivo será salvo"""
        spider_name = info.spider.name
        year = item.get('year', 'unknown')
        number = item.get('number', 'unknown')
        type_ = item.get('type', 'unknown')
        normalized_type = type_.lower().replace(' ', '-').replace('º', '') if type_ else 'unknown'
        filename = f"{normalized_type}-{number}-{year}.pdf"
        
        return f"{spider_name}/pdf/{year}/{filename}"
    
    def item_completed(self, results, item, info):
        """Adiciona informações dos arquivos baixados ao item"""
        file_paths = [x['path'] for ok, x in results if ok]
        info.spider.logger.info(f"Files downloaded for {item.get('number')}: {file_paths}")
        if file_paths:
            item['pdf_files'] = file_paths
        return item


class GeminiPDFExtractionPipeline:
    """Pipeline que usa Google Gemini para extrair texto de PDFs"""
    
    def __init__(self):
        # Configurar API do Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no arquivo .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.files_dir = 'storage/downloads'  # Para acessar arquivos
        
        # Prompt para extração de texto legislativo
        self.extraction_prompt = """
Você é um assistente especializado em extrair texto de documentos legislativos brasileiros.

Extraia o texto completo deste documento PDF, preservando:
- A estrutura de artigos, parágrafos e incisos
- Numeração e formatação legal
- Texto de justificativas e ementas

Retorne apenas o texto extraído em formato markdown, sem comentários adicionais.
Organize o texto de forma clara e estruturada.
"""
    
    def process_item(self, item, spider):
        """Processa PDFs baixados e extrai texto usando Gemini"""
        pdf_files = item.get('pdf_files', [])
        spider.logger.info(f"Gemini processing item {item.get('number')}, pdf_files: {pdf_files}")

        if not pdf_files:
            item['full_text'] = "[FALHA] Nenhum arquivo PDF encontrado para extração."
            return item

        # Assume um arquivo PDF por item
        pdf_path = pdf_files[0]
        full_pdf_path = os.path.join(self.files_dir, pdf_path)
        spider.logger.info(f"Processing PDF: {full_pdf_path}, exists: {os.path.exists(full_pdf_path)}")

        # Upload do arquivo para Gemini
        uploaded_file = genai.upload_file(full_pdf_path)

        # Gera conteúdo com o prompt
        response = self.model.generate_content([uploaded_file, self.extraction_prompt])

        # Extrai o texto da resposta
        item['full_text'] = response.text


        return item


class MarkdownWriterPipeline:
    """Pipeline que salva o texto extraído em arquivo .md"""

    def process_item(self, item, spider):
        """Salva full_text em arquivo .md se md_files estiver definido"""
        full_text = item.get('full_text', '').strip()
        md_files = item.get('md_files')

        if not full_text or not md_files:
            return item

        # Caminho completo: storage/output/{md_files}
        full_path = os.path.join('storage', 'output', md_files)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        return item


class TestItemCollectorPipeline:
    """Pipeline to collect items in memory for testing (not for production)."""

    def __init__(self):
        self.items = []

    def open_spider(self, spider):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

        # Caminho completo: storage/downloads/{caminho}
        full_path = os.path.join('storage', 'downloads', caminho)
        dir_path = os.path.dirname(full_path)

        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            spider.logger.info(f"Texto salvo em .md: {full_path} ({len(full_text)} caracteres)")
        except Exception as e:
            spider.logger.error(f"Erro ao salvar .md {full_path}: {str(e)}")

        return item
        
        extracted_texts = []
        files_dir = spider.settings.get('FILES_STORE', 'downloads')
        
        for file_path in files:
            full_path = os.path.join(files_dir, file_path)
            
            if not os.path.exists(full_path):
                spider.logger.warning(f"Arquivo não encontrado: {full_path}")
                continue
            
            try:
                # Upload do arquivo para o Gemini
                spider.logger.info(f"Processando PDF: {file_path}")
                uploaded_file = genai.upload_file(full_path)
                
                # Extrair texto usando o modelo
                response = self.model.generate_content([
                    self.extraction_prompt,
                    uploaded_file
                ])
                
                extracted_text = response.text
                extracted_texts.append(extracted_text)
                
                spider.logger.info(f"Texto extraído com sucesso de {file_path} ({len(extracted_text)} caracteres)")
                
                # Limpar arquivo do Gemini
                genai.delete_file(uploaded_file.name)
                
            except Exception as e:
                spider.logger.error(f"Erro ao processar {file_path}: {str(e)}")
                continue
        
        # Combinar todos os textos extraídos
        if extracted_texts:
            item['full_text'] = "\n\n---\n\n".join(extracted_texts)
            item['length'] = len(item['full_text'])
            spider.logger.info(f"Texto completo extraído: {item['length']} caracteres")
        else:
            spider.logger.warning(f"Nenhum texto foi extraído para {item.get('title')}")
            item['full_text'] = ""
            item['length'] = 0
        
        return item