import argparse
import json
import weaviate
import os
import tiktoken
from datetime import datetime
from weaviate.util import generate_uuid5
import weaviate.classes.config as wc
from weaviate.classes.config import Configure
from weaviate.classes.init import Auth
from dotenv import load_dotenv
from tqdm import tqdm
from collections import Counter

load_dotenv()

def chunk_text(text, max_tokens=3000, overlap_tokens=150, model="text-embedding-ada-002"):
    """Divide o texto em chunks baseados em tokens do modelo OpenAI."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    chunks = []
    i = 0
    while i < len(tokens):
        end = min(i + max_tokens, len(tokens))
        chunk_tokens = tokens[i:end]
        chunk = encoding.decode(chunk_tokens)
        if end < len(tokens):
            pos = chunk.rfind(' ')
            if pos != -1:
                chunk = chunk[:pos+1]
                used = encoding.encode(chunk)
                end = i + len(used)
        chunks.append({"text": chunk, "number": len(chunks)})
        if end >= len(tokens):
            break
        i = end - overlap_tokens
        overlap = encoding.decode(tokens[i:i+overlap_tokens])
        sp = overlap.find(' ')
        if sp != -1:
            adj = sp + 1
            i += len(encoding.encode(overlap[:adj])) - overlap_tokens
    return chunks


def load_jl_items(jsonl_file):
    """Carrega itens do arquivo JSON Lines."""
    items = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def map_item_to_proposicao(item):
    """Mapeia item do .jl para formato ProposicaoItem."""
    # Read markdown content
    md_path = os.path.join('./storage/downloads/md', item['caminho_arquivo_texto'])
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except FileNotFoundError:
        full_text = ""

    # Extract year from data_documento
    year = int(item['data_documento'].split('-')[0]) if item.get('data_documento') else None

    # Map authors
    authors = [a['nome'] for a in item['autores']] if item['autores'] else []

    return {
        'title': item.get('ementa', ''),
        'house': item.get('casa_legislativa', ''),
        'type': item.get('tipo_documento', ''),
        'number': int(item['numero_documento']) if item.get('numero_documento') else None,
        'presentation_date': item.get('data_documento'),
        'year': year,
        'author': authors,
        'subject': item.get('ementa', ''),  # Using ementa as subject since assuntos is empty
        'full_text': full_text,
        'length': len(full_text),
        'url': item.get('url_documento_original'),
        'scraped_at': item.get('data_raspagem'),
    }


def setup_schema(client, class_name, vector_config, reset=False):
    """Cria ou reseta a classe no Weaviate com propriedades incluindo chunks."""
    if reset:
        try:
            client.collections.delete(class_name)
            print(f"Coleção '{class_name}' resetada.")
        except Exception:
            pass
    if not client.collections.exists(class_name):
        props = [
            wc.Property(name='title', data_type=wc.DataType.TEXT),
            wc.Property(name='house', data_type=wc.DataType.TEXT),
            wc.Property(name='type', data_type=wc.DataType.TEXT),
            wc.Property(name='number', data_type=wc.DataType.INT),
            wc.Property(name='presentation_date', data_type=wc.DataType.TEXT),
            wc.Property(name='year', data_type=wc.DataType.INT),
            wc.Property(name='author', data_type=wc.DataType.TEXT_ARRAY),
            wc.Property(name='subject', data_type=wc.DataType.TEXT),
            wc.Property(name='full_text', data_type=wc.DataType.TEXT),
            wc.Property(name='length', data_type=wc.DataType.INT),
            wc.Property(name='url', data_type=wc.DataType.TEXT),
            wc.Property(name='scraped_at', data_type=wc.DataType.TEXT),
            # Propriedades de chunk
            wc.Property(name='chunk_text', data_type=wc.DataType.TEXT),
            wc.Property(name='chunk_number', data_type=wc.DataType.INT),
        ]
        client.collections.create(
            name=class_name,
            properties=props,
            vectorizer_config=vector_config
        )
        print(f"Coleção '{class_name}' criada com chunks.")
    else:
        print(f"Coleção '{class_name}' já existe. Pulando criação.")


def import_items(client, class_name, items, batch_size=10, dry_run=False):
    """Importa itens e seus chunks no Weaviate."""
    collection = client.collections.get(class_name)
    total_chunks = 0
    imported_items = 0
    skipped_items = 0
    with collection.batch.fixed_size(batch_size=batch_size) as batch:
        for item in tqdm(items):
            proposicao = map_item_to_proposicao(item)
            full = proposicao.get('full_text', '')
            if not full.strip():
                skipped_items += 1
                continue  # Skip silently if no text
            imported_items += 1
            chunks = chunk_text(full)
            for chunk in chunks:
                props = {
                    'title': proposicao.get('title'),
                    'house': proposicao.get('house'),
                    'type': proposicao.get('type'),
                    'number': proposicao.get('number'),
                    'presentation_date': proposicao.get('presentation_date'),
                    'year': proposicao.get('year'),
                    'author': proposicao.get('author'),
                    'subject': proposicao.get('subject'),
                    'full_text': full,
                    'length': proposicao.get('length'),
                    'url': proposicao.get('url'),
                    'scraped_at': proposicao.get('scraped_at'),
                    'chunk_text': chunk['text'],
                    'chunk_number': chunk['number'],
                }
                uuid = generate_uuid5(chunk['text'])
                if dry_run:
                    print(f"DRY RUN: chunk {chunk['number']} -> UUID: {uuid}")
                else:
                    batch.add_object(properties=props, uuid=uuid)
                total_chunks += 1

            if batch.number_errors > 10:
                print("Batch import stopped due to excessive errors.")
                break

        failed_objects = collection.batch.failed_objects
        if failed_objects:
            print(f"Number of failed imports: {len(failed_objects)}")
            print(f"First failed object: {failed_objects[0:5]}")

    print(f"Importação finalizada: {imported_items} itens importados, {skipped_items} itens pulados (sem texto), {total_chunks} chunks.")


def main():
    parser = argparse.ArgumentParser(
        description="Importa JSON Lines de proposições com chunking para o Weaviate"
    )
    parser.add_argument("--input", required=True,
                         help="Arquivo JSON Lines (.jl)")
    parser.add_argument("--reset", action="store_true",
                         help="Reseta a classe antes de criar")
    parser.add_argument("--dry_run", action="store_true",
                         help="Apenas imprime UUID sem inserir")
    parser.add_argument("--stats", action="store_true",
                         help="Mostra estatísticas dos PLs (itens com/sem texto)")
    args = parser.parse_args()

    items = load_jl_items(args.input)

    if args.stats:
        print("Calculando estatísticas...")
        total_items = len(items)
        with_text = 0
        without_text = 0
        total_length = 0
        type_counts = Counter()
        year_counts = Counter()
        for item in items:
            type_counts[item.get('tipo_documento', 'Desconhecido')] += 1
            year = int(item['data_documento'].split('-')[0]) if item.get('data_documento') else None
            if year:
                year_counts[year] += 1
            proposicao = map_item_to_proposicao(item)
            full_text = proposicao.get('full_text', '')
            if full_text.strip():
                with_text += 1
                total_length += len(full_text)
            else:
                without_text += 1
        avg_length = total_length / with_text if with_text > 0 else 0
        print(f"Total de itens: {total_items}")
        print(f"Documentos por tipo: {dict(type_counts)}")
        print(f"Documentos por ano: {dict(year_counts)}")
        print(f"Tamanho médio do texto: {avg_length:.2f} caracteres")
        print(f"Projetos sem texto: {without_text}")
    else:
        # Load config from .env
        config = {
            "weaviate_url": os.getenv("WEAVIATE_URL", ""),
            "weaviate_apikey": os.getenv("WEAVIATE_API_KEY", ""),
            "class_name": os.getenv("WEAVIATE_CLASS", "Bill"),
            "openai_apikey": os.getenv("OPENAI_APIKEY", ""),
        }

        headers = {"X-OpenAI-Api-Key": config.get("openai_apikey")} if config.get("openai_apikey") else {}
        auth = Auth.api_key(api_key=config.get("weaviate_apikey")) if config.get("weaviate_apikey") else None

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=config.get("weaviate_url"),
            auth_credentials=auth,
            headers=headers,
            additional_config=weaviate.config.AdditionalConfig(timeout=weaviate.config.Timeout(insert=300))
        )
        print(f"Conectado a Weaviate em {config.get('weaviate_url')}")

        vec_conf = [
            Configure.NamedVectors.text2vec_openai(
                name="chunk_vector",
                source_properties=["title","subject","chunk_text"]
            )]
        setup_schema(client, config.get("class_name"), vec_conf, reset=args.reset)
        import_items(client, config.get("class_name"), items, dry_run=args.dry_run)

        client.close()


if __name__ == '__main__':
    main()