import argparse
import json
import statistics
from datetime import datetime
import tiktoken
from collections import Counter

REQUIRED_FIELDS = ['title', 'house', 'type', 'number', 'presentation_date', 'year', 'author', 'subject', 'full_text', 'url', 'scraped_at', 'emenda']

def validate_item(item):
    missing_required = [f for f in REQUIRED_FIELDS if not item.get(f)]
    critical_missing = {'emenda', 'full_text', 'house'}
    if missing_required and set(missing_required).issubset(critical_missing):
        return 'invalid', missing_required
    elif missing_required:
        return 'incomplete', missing_required
    else:
        return 'complete', missing_required

def calculate_stats(items):
    total_projects = len(items)
    complete_projects = 0
    incomplete_projects = 0
    invalid_projects = 0
    text_lengths = []
    token_lengths = []
    houses = Counter()
    types = Counter()
    years = Counter()
    dates = []
    scraped_dates = []

    encoding = tiktoken.get_encoding("cl100k_base")

    for item in items:
        status, missing = validate_item(item)
        if status == 'complete':
            complete_projects += 1
            full_text = item.get('full_text', '')
            text_lengths.append(len(full_text))
            tokens = encoding.encode(full_text)
            token_lengths.append(len(tokens))
            houses[item.get('house')] += 1
            types[item.get('type')] += 1
            years[item.get('year')] += 1
            try:
                dates.append(datetime.fromisoformat(item.get('presentation_date')))
            except:
                pass
            try:
                scraped_dates.append(datetime.fromisoformat(item.get('scraped_at')))
            except:
                pass
        elif status == 'incomplete':
            incomplete_projects += 1
            print(f"Item incompleto (ID aproximado: {item.get('number', 'N/A')}): campos faltantes: {missing}")
        elif status == 'invalid':
            invalid_projects += 1
            print(f"Item inválido (ID aproximado: {item.get('number', 'N/A')}): campos faltantes: {missing}")

    avg_text_len = statistics.mean(text_lengths) if text_lengths else 0
    avg_token_len = statistics.mean(token_lengths) if token_lengths else 0
    date_range = max(dates) - min(dates) if dates else None

    return {
        'total_projects': total_projects,
        'complete_projects': complete_projects,
        'incomplete_projects': incomplete_projects,
        'invalid_projects': invalid_projects,
        'avg_text_length_chars': avg_text_len,
        'avg_text_length_tokens': avg_token_len,
        'houses_distribution': dict(houses),
        'types_distribution': dict(types),
        'years_distribution': dict(years),
        'presentation_date_range': str(date_range) if date_range else 'N/A'
    }

def main():
    parser = argparse.ArgumentParser(description="Valida e resume arquivo JSON de proposições")
    parser.add_argument('--input', required=True, help="Caminho para o arquivo JSON")
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except FileNotFoundError:
        print(f"Arquivo {args.input} não encontrado.")
        return
    except json.JSONDecodeError:
        print(f"Erro ao decodificar JSON em {args.input}.")
        return

    stats = calculate_stats(items)
    print("Resumo do JSON:")
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == '__main__':
    main()