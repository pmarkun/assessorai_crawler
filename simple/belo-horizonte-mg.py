#!/usr/bin/env python3
"""
Simple Scraper for Legislative Proposals - Belo Horizonte MG

This script scrapes legislative proposals from the Câmara Municipal de Belo Horizonte, MG.
It processes the specified page of a proposals list, extracts metadata for each proposal, and prints the results.

Usage:
    python belo-horizonte-mg.py --page 1 --tipo "Projeto de Lei" --ano 2025

Arguments:
- --page: Page number to scrape (default: 1)
- --tipo: Document type (default: Projeto de Lei)
- --ano: Year to filter proposals (optional, if not provided, no year filter)

Features:
- Extracts proposal metadata from table rows.
- Finds next page URL and total pages from pagination.
- Uses requests for HTTP requests and lxml for HTML parsing.
- Prints results using pprint for readability.

This serves as a scraper for Belo Horizonte MG system.
"""

import argparse
import requests
import re
from datetime import datetime
import hashlib
from lxml import html
import pprint

def extract_metadata_from_li(li, base_url):
    """
    Extracts metadata from a list item element.

    Args:
        li: lxml element representing a list item (<li>).
        base_url: Base URL of the page for resolving relative links.

    Returns:
        dict: Dictionary with extracted proposal metadata, or None if extraction fails.
    """
    item = {}

    # Find the title span
    title_span = li.cssselect('span.detalhar.vinculavel')
    if not title_span:
        return None

    texto_titulo_completo = title_span[0].text_content().strip()
    link_detalhes = title_span[0].get('data-caminho', '')

    # Parse title to extract type, number, year (e.g., "Projeto de Lei - 123/2025")
    match_titulo = re.search(r'(.+?)\s*-\s*(\d+)/(\d{4})', texto_titulo_completo)
    if match_titulo:
        item['type'] = match_titulo.group(1).strip()
        item['number'] = str(match_titulo.group(2))
        item['year'] = str(match_titulo.group(3))
        item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
    else:
        # Fallback
        item['title'] = texto_titulo_completo
        item['number'] = None
        item['year'] = None
        item['type'] = None

    # Extract other metadata from <p> tags with <strong>
    ps = li.cssselect('p')
    for p in ps:
        text = p.text_content().strip()
        if text.startswith('Autoria:'):
            item['author'] = [text.replace('Autoria:', '').strip()]
        elif text.startswith('Assunto:'):
            item['subject'] = text.replace('Assunto:', '').strip()
        elif text.startswith('Data de apresentação:'):
            item['presentation_date'] = text.replace('Data de apresentação:', '').strip()

    # Extract PDF URL
    pdf_links = li.cssselect('a[title*="Baixar texto inicial"]')
    if pdf_links:
        pdf_url = pdf_links[0].get('href')
        item['url'] = pdf_url
        item['file_urls'] = [item['url']]

    # Set fixed fields
    item['house'] = 'Câmara Municipal de Belo Horizonte'
    item['scraped_at'] = datetime.now().isoformat()

    # Generate unique ID based on project URL
    item['uuid'] = hashlib.md5(link_detalhes.encode('utf-8')).hexdigest()
    item['project_url'] = link_detalhes

    # Generate path for markdown file
    uf = 'MG'
    slug = 'mg-belo-horizonte'
    normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
    item['md_files'] = f"{uf}/{slug}/{normalized_type}-{item['number']}-{item['year']}.md"

    return item

def main():
    parser = argparse.ArgumentParser(description='Simple scraper for legislative proposals - Belo Horizonte MG')
    parser.add_argument('--page', type=int, default=1, help='Page number to scrape (default: 1)')
    parser.add_argument('--tipo', type=str, default='Projeto de Lei', help='Document type (default: Projeto de Lei)')
    parser.add_argument('--ano', type=int, help='Year to filter proposals (optional)')
    args = parser.parse_args()

    # Build the URL
    url = "https://www.cmbh.mg.gov.br/sites/all/modules/proposicoes/pesquisar.php"
    base_url = "https://www.cmbh.mg.gov.br"

    # Data for POST
    data = {
        'tipo': '2c907f7801d41f2001024943e5ec004a',  # Projeto de Lei
        'numero': '[número]',
        'ano': '[ano]',
        'buscarPorProtocolo': 'false',
        'autor': '[autor]',
        'assunto': '[assunto]',
        'assunto2': '[assunto2]',
        'fase': '[Selecione]',
        'tramitando': 'Tanto faz',
        'buscarProposicoesOpinar': 'false',
        'paginaRequerida': args.page,
        'metodo': '',
        'nomeProposicao': '',
        'urlProposicao': '',
        'idProposicao': '',
        'buscarEmendas_proposicoes': '',
        'idTipoEmenda': '',
        'idTipoSubemenda': '',
        'idTipoEmendaDeRedacao': '',
        'drupalUsername': 'deslogado-anonimo',
        'drupalEmail': '',
        'buscaViaUrl': '',
        'stormCodex': '410d41a2a8d879f46dc8675cb1ea8030',
        'mobile': '0'
    }
    if args.ano:
        data['ano'] = args.ano

    print(f"DEBUG: Starting scraper with URL: {url}")
    print(f"DEBUG: Data: {data}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.cmbh.mg.gov.br/atividade-legislativa/pesquisar-proposicoes',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.cmbh.mg.gov.br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # Fetch the page content via POST
    print("DEBUG: Making POST request to the URL")
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    response.encoding = 'utf-8'
    print("DEBUG: Request successful, status code:", response.status_code)

    # Parse the HTML response
    print("DEBUG: Parsing HTML content with lxml")
    html_string = response.content.decode('utf-8')
    print("DEBUG: Response contains 'Projeto de Lei':", 'Projeto de Lei' in html_string)
    print("DEBUG: Response snippet:", html_string[:2000])
    tree = html.fromstring(html_string)

    # Select list items containing proposals
    print("DEBUG: Selecting list items")
    linhas = tree.cssselect('ul.lista-pesquisas li')
    print(f"DEBUG: Found {len(linhas)} items in the list")

    results = []

    # Process each item to extract proposal data
    print(f"DEBUG: Processing all items in page {args.page}")
    for i, linha in enumerate(linhas):
        print(f"DEBUG: Processing item {i+1}")
        print(f"DEBUG: Item text: {linha.text_content().strip()[:200]}")
        item = extract_metadata_from_li(linha, base_url)
        if item:
            print(f"DEBUG: Extracted item: {item['title']}")
            results.append(item)
        else:
            print("DEBUG: No item extracted from this item")

    print(f"DEBUG: Total results extracted: {len(results)}")

    # Pagination: assume 10 per page, check if there are more
    # For simplicity, assume next page if results == 10
    next_page_url = None
    if len(results) == 10:
        next_page_url = f"Page {args.page + 1}"
        print(f"DEBUG: Next page: {next_page_url}")

    total_pages = None  # Unknown

    print("Next page:", next_page_url)
    print("Total pages:", total_pages)

    # Print extracted results
    for i, result in enumerate(results):
        print(f"DEBUG: Printing result {i+1}")
        pprint.pprint(result)

if __name__ == '__main__':
    main()