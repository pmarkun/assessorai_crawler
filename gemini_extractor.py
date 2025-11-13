import argparse
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm

load_dotenv()

class GeminiExtractor:
    """Serviço para extrair texto de PDFs usando Google Gemini"""

    def __init__(self):
        # Configurar API do Gemini
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
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

    def extract_text_from_pdf(self, pdf_path):
        """Extrai texto de um PDF usando Gemini"""
        if not self.api_key or not self.model:
            raise Exception("Gemini API key não configurada")

        if not os.path.exists(pdf_path):
            raise Exception(f"Arquivo PDF não encontrado: {pdf_path}")

        try:
            # Upload do arquivo para Gemini
            uploaded_file = genai.upload_file(pdf_path)

            # Gera conteúdo com o prompt
            response = self.model.generate_content([uploaded_file, self.extraction_prompt])

            # Extrai o texto da resposta
            extracted_text = response.text

            # Limpar arquivo do Gemini
            genai.delete_file(uploaded_file.name)

            return extracted_text

        except Exception as e:
            raise Exception(f"Erro ao processar PDF {pdf_path}: {str(e)}")

    def process_item(self, item, output_dir='storage/output', overwrite=False):
        """Processa um item, extraindo texto se necessário"""
        # Verifica se já tem texto extraído
        if item.get('full_text') and item.get('md_files') and not overwrite:
            print(f"Pulando item {item.get('number')} - já processado")
            return item

        # Garante md_files
        if not item.get('md_files'):
            # Gera caminho baseado nos campos do item
            house = item.get('house', 'unknown').lower().replace(' ', '-')
            year = item.get('year', 'unknown')
            type_ = item.get('type', 'unknown').lower().replace(' ', '-').replace('º', '')
            number = item.get('number', 'unknown')
            md_filename = f"{type_}-{number}-{year}.md"
            item['md_files'] = f"{house}/md/{year}/{md_filename}"

        pdf_files = item.get('pdf_files', [])
        if not pdf_files:
            print(f"Nenhum PDF encontrado para item {item.get('number')}")
            return item

        # Assume um arquivo PDF por item
        pdf_path = pdf_files[0]
        full_pdf_path = os.path.join(self.files_dir, pdf_path)

        try:
            extracted_text = self.extract_text_from_pdf(full_pdf_path)

            # Salva em MD
            full_md_path = os.path.join(output_dir, item['md_files'])
            os.makedirs(os.path.dirname(full_md_path), exist_ok=True)
            with open(full_md_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)

            # Atualiza item
            item['full_text'] = extracted_text
            item['length'] = len(extracted_text)

            print(f"Texto extraído para item {item.get('number')} - {len(extracted_text)} caracteres")

        except Exception as e:
            print(f"Erro processando item {item.get('number')}: {str(e)}")

        return item

    def process_json_file(self, json_file, output_dir='storage/output', overwrite=False):
        """Processa todos os itens de um arquivo JSON"""
        if not os.path.exists(json_file):
            raise Exception(f"Arquivo JSON não encontrado: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            items = json.load(f)

        processed_items = []
        for item in tqdm(items):
            processed_item = self.process_item(item, output_dir, overwrite)
            processed_items.append(processed_item)

        # Salva JSON atualizado
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(processed_items, f, ensure_ascii=False, indent=2)

        print(f"Processamento concluído. {len(processed_items)} itens processados.")

def main():
    parser = argparse.ArgumentParser(
        description="Extrai texto de PDFs usando Google Gemini"
    )
    parser.add_argument("--input", required=True,
                        help="Arquivo JSON com os itens a processar")
    parser.add_argument("--output", default="storage/output",
                        help="Diretório de saída para arquivos MD (padrão: storage/output)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Reprocessa itens já processados")
    args = parser.parse_args()

    extractor = GeminiExtractor()
    extractor.process_json_file(args.input, args.output, args.overwrite)

if __name__ == '__main__':
    main()