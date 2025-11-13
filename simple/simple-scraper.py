#!/usr/bin/env python3
"""
Simple Scraper for Legislative Proposals

This script scrapes legislative proposals from a SAPL-based system (e.g., Fortaleza's municipal chamber).
It processes the specified page of a proposals list, extracts metadata for each proposal, and prints the results.

Usage:
    python simple-scraper.py --page 1 --tipo 1 --ano 2023

Arguments:
- --page: Page number to scrape (default: 1)
- --tipo: Document type ID (default: 1, e.g., 1 for Projeto de Lei Ordinária)
- --ano: Year to filter proposals (optional, if not provided, no year filter)

Features:
- Extracts proposal metadata from table rows.
- Finds next page URL and total pages from pagination.
- Uses requests for HTTP requests and lxml for HTML parsing.
- Prints results using pprint for readability.

This serves as a base for other scrapers targeting similar SAPL systems.
"""

import argparse
import requests
import re
from datetime import datetime
import hashlib
from lxml import html
import pprint

def extract_metadata_from_row(row, base_url):
    """
    Extracts metadata from a table row element.

    Args:
        row: lxml element representing a table row (<tr>).
        base_url: Base URL of the page for resolving relative links.

    Returns:
        dict: Dictionary with extracted proposal metadata, or None if extraction fails.

    Extracts fields like title, number, year, type, subject, presentation_date, author,
    PDF URL, house, scraped_at timestamp, UUID, project_url, and md_files path.
    """
    item = {}

    # Find the main link in the row (usually the proposal title link)
    link_titulo_tag = row.cssselect('a')
    if not link_titulo_tag:
        return None

    texto_titulo_completo = link_titulo_tag[0].text_content().strip()
    link_detalhes_relativo = link_titulo_tag[0].get('href', '')

    # Parse title to extract type, number, year (e.g., "Projeto 123/2023 - Lei Ordinária")
    match_titulo = re.search(r'(\w+)\s+(\d+)/(\d{4})\s+-\s+(.*)', texto_titulo_completo)
    if match_titulo:
        item['number'] = str(match_titulo.group(2))
        item['year'] = str(match_titulo.group(3))
        item['type'] = match_titulo.group(4).strip()
        item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
    else:
        # Fallback if regex doesn't match
        item['title'] = texto_titulo_completo
        item['number'] = None
        item['year'] = None
        item['type'] = None

    # Extract subject from the specific div
    item['subject'] = row.cssselect('div.dont-break-out')[0].text_content().strip() if row.cssselect('div.dont-break-out') else ''

    # Extract presentation date and author from strong labels
    item['presentation_date'] = row.xpath("string(.//strong[contains(text(), 'Apresentação:')]/following-sibling::text()[1])").strip()
    item['author'] = [row.xpath("string(.//strong[contains(text(), 'Autor:')]/following-sibling::text()[1])").strip()]

    # Extract PDF URL if available
    pdf_relative_url = row.xpath('.//a[contains(text(), "Texto Original")]/@href')
    if pdf_relative_url:
        pdf_relative_url = pdf_relative_url[0]
        item['url'] = base_url.rstrip('/') + '/' + pdf_relative_url.lstrip('/')
        item['file_urls'] = [item['url']]

    # Set fixed fields for Fortaleza
    item['house'] = 'Câmara Municipal de Fortaleza'
    item['scraped_at'] = datetime.now().isoformat()

    # Generate unique ID based on project URL
    item['uuid'] = hashlib.md5((base_url + link_detalhes_relativo).encode('utf-8')).hexdigest()
    item['project_url'] = base_url + link_detalhes_relativo

    # Generate path for markdown file
    uf = 'CE'
    slug = 'ce-fortaleza'
    normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
    item['md_files'] = f"{uf}/{slug}/{normalized_type}-{item['number']}-{item['year']}.md"

    return item

def main():
    """
    Main function to run the scraper.

    Parses command-line arguments, builds the URL, fetches the page, extracts proposals,
    finds pagination info, and prints the results.
    """
    parser = argparse.ArgumentParser(description='Simple scraper for legislative proposals')
    parser.add_argument('--page', type=int, default=1, help='Page number to scrape (default: 1)')
    parser.add_argument('--tipo', type=int, default=1, help='Document type ID (default: 1)')
    parser.add_argument('--ano', type=int, help='Year to filter proposals (optional)')
    args = parser.parse_args()

    # Build the URL
    base_url = "https://sapl.fortaleza.ce.leg.br/materia/pesquisar-materia"
    url = f"{base_url}?page={args.page}&tipo={args.tipo}"
    if args.ano:
        url += f"&ano={args.ano}"

    # Start debug logging
    print(f"DEBUG: Starting scraper with URL: {url}")

    # Fetch the page content
    print("DEBUG: Making GET request to the URL")
    response = requests.get(url)
    response.raise_for_status()
    print("DEBUG: Request successful, status code:", response.status_code)

    # Parse the HTML
    print("DEBUG: Parsing HTML content with lxml")
    tree = html.fromstring(response.content)

    # Select table rows containing proposals
    print("DEBUG: Selecting table rows with 'table.table-striped tr'")
    linhas = tree.cssselect('table.table-striped tr')
    print(f"DEBUG: Found {len(linhas)} rows in the table")

    results = []

    # Process each row to extract proposal data
    print(f"DEBUG: Processing all rows in page {args.page}")
    for i, linha in enumerate(linhas):
        print(f"DEBUG: Processing row {i+1}")
        item = extract_metadata_from_row(linha, url)
        if item:
            print(f"DEBUG: Extracted item: {item['title']}")
            results.append(item)
        else:
            print("DEBUG: No item extracted from this row")

    print(f"DEBUG: Total results extracted: {len(results)}")

    # Extract next page URL from pagination
    next_page_link = tree.cssselect('a.page-link:contains("Próxima")')
    next_page_url = None
    if next_page_link:
        href = next_page_link[0].get('href')
        if href:
            # Resolve relative URL
            next_page_url = base_url + href if href.startswith('?') else href
            print(f"DEBUG: Next page URL: {next_page_url}")

    # Extract total pages from pagination text (e.g., "Página 1 de 10")
    total_pages = None
    pagination_text = tree.xpath("string(.//div[contains(@class, 'pagination')]//span[contains(text(), 'de')])")
    if pagination_text:
        match = re.search(r'de\s+(\d+)', pagination_text)
        if match:
            total_pages = int(match.group(1))
            print(f"DEBUG: Total pages: {total_pages}")

    # Output pagination info
    print("Next page URL:", next_page_url)
    print("Total pages:", total_pages)

    # Print extracted results
    for i, result in enumerate(results):
        print(f"DEBUG: Printing result {i+1}")
        pprint.pprint(result)

if __name__ == '__main__':
    main()