#!/usr/bin/env python3
"""
Simple Scraper for Legislative Proposals - Atibaia SP

This script scrapes legislative proposals from the Câmara Municipal de Atibaia, SP.
It processes the specified page of a proposals list, extracts metadata for each proposal, and prints the results.

Usage:
    python atibaia-sp.py --page 1 --tipo 10 --ano 2025

Arguments:
- --page: Page number to scrape (default: 1)
- --tipo: Document type ID (default: 10, Projeto de Lei)
- --ano: Year to filter proposals (optional, if not provided, no year filter)

Features:
- Extracts proposal metadata from page sections.
- Finds next page URL and total pages from pagination.
- Uses requests for HTTP requests and lxml for HTML parsing.
- Prints results using pprint for readability.

This serves as a scraper for Atibaia SP system.
"""

import argparse
import requests
import re
from datetime import datetime
import hashlib
from lxml import html
import pprint

def extract_metadata_from_block(block, base_url):
    """
    Extracts metadata from a project block element.

    Args:
        block: lxml element representing a project block.
        base_url: Base URL of the page.

    Returns:
        dict: Dictionary with extracted proposal metadata, or None if extraction fails.
    """
    # Extract title
    h4 = block.cssselect('h4')
    if not h4:
        return None
    texto_titulo = h4[0].text_content().strip()
    match_titulo = re.search(r'Projeto de Lei Nº (\d+)-(\d{4})', texto_titulo)
    if not match_titulo:
        return None
    item = {}
    item['number'] = str(match_titulo.group(1))
    item['year'] = str(match_titulo.group(2))
    item['type'] = 'Projeto de Lei'
    item['title'] = f"Projeto de Lei nº {item['number']}/{item['year']}"

    # Extract data inicial
    data_elem = block.xpath('.//h4[contains(text(), "Data Inicial:")]/following-sibling::text()[1]')
    item['presentation_date'] = data_elem[0].strip() if data_elem else ''

    # Extract autor
    autor_elem = block.xpath('.//h4[contains(text(), "Autor:")]/following-sibling::text()[1]')
    item['author'] = [autor_elem[0].strip()] if autor_elem else ['']

    # Extract ementa
    ementa_elem = block.xpath('.//h4[contains(text(), "Ementa:")]/following-sibling::text()[1]')
    item['subject'] = ementa_elem[0].strip() if ementa_elem else ''

    # Extract link to details
    link_elem = block.cssselect('a')
    project_url = ''
    if link_elem:
        href = link_elem[0].get('href')
        if href:
            project_url = base_url.rstrip('?') + href if href.startswith('?') else href

    item['project_url'] = project_url

    # Extract file_urls from the form
    file_urls = []
    form = block.cssselect('form')
    if form:
        action = form[0].get('action')
        inputs = form[0].cssselect('input')
        params = {}
        for inp in inputs:
            name = inp.get('name')
            value = inp.get('value')
            if name and value is not None:
                params[name] = value
        if action and params:
            query = '&'.join(f"{k}={v}" for k, v in params.items())
            file_url = f"{action}?{query}"
            file_urls.append(file_url)
    item['file_urls'] = file_urls

    # Set fixed fields
    item['house'] = 'Câmara Municipal de Atibaia'
    item['scraped_at'] = datetime.now().isoformat()
    item['uuid'] = hashlib.md5(project_url.encode('utf-8')).hexdigest() if project_url else ''

    # md_files
    uf = 'SP'
    slug = 'sp-atibaia'
    normalized_type = 'projeto-de-lei'
    item['md_files'] = f"{uf}/{slug}/{normalized_type}-{item['number']}-{item['year']}.md"

    return item

def main():
    parser = argparse.ArgumentParser(description='Simple scraper for legislative proposals - Atibaia SP')
    parser.add_argument('--page', type=int, default=1, help='Page number to scrape (default: 1)')
    parser.add_argument('--tipo', type=int, default=10, help='Document type ID (default: 10)')
    parser.add_argument('--ano', type=int, help='Year to filter proposals (optional)')
    args = parser.parse_args()

    # Build the URL
    base_url = "https://www.camaraatibaia.sp.gov.br/"
    params = f"pag=T1RFPU9UVT1PVEk9T0dZPU9HRT1PV0k9T1RZPQ==&view=getTPT&tp={args.tipo}&estado=tramitado"
    if args.ano:
        params += f"&ano={args.ano}"
    params += f"&pg={args.page}"
    url = f"{base_url}?{params}"

    print(f"DEBUG: Starting scraper with URL: {url}")

    # Fetch the page content
    print("DEBUG: Making GET request to the URL")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    print("DEBUG: Request successful, status code:", response.status_code)

    # Parse the HTML
    print("DEBUG: Parsing HTML content with lxml")
    tree = html.fromstring(response.content)

    # Find all project tds
    blocks = tree.xpath("//td[.//h4[contains(text(), 'Projeto de Lei Nº')]]")

    print(f"DEBUG: Found {len(blocks)} project blocks")

    results = []

    # Process each block
    print(f"DEBUG: Processing all blocks in page {args.page}")
    for i, block in enumerate(blocks):
        print(f"DEBUG: Processing block {i+1}")
        item = extract_metadata_from_block(block, base_url)
        if item:
            print(f"DEBUG: Extracted item: {item['title']}")
            results.append(item)
        else:
            print("DEBUG: No item extracted from this block")

    print(f"DEBUG: Total results extracted: {len(results)}")

    # Pagination
    next_page_link = tree.cssselect('a:contains("Próxima")')
    next_page_url = None
    if next_page_link:
        href = next_page_link[0].get('href')
        if href:
            next_page_url = base_url + href if href.startswith('?') else href
            print(f"DEBUG: Next page URL: {next_page_url}")

    total_pages = None
    # Find total pages from pagination
    page_links = tree.cssselect('a[href*="pg="]')
    if page_links:
        pages = []
        for link in page_links:
            href = link.get('href')
            match = re.search(r'pg=(\d+)', href)
            if match:
                pages.append(int(match.group(1)))
        if pages:
            total_pages = max(pages)
            print(f"DEBUG: Total pages: {total_pages}")

    print("Next page URL:", next_page_url)
    print("Total pages:", total_pages)

    # Print results
    for i, result in enumerate(results):
        print(f"DEBUG: Printing result {i+1}")
        pprint.pprint(result)

if __name__ == '__main__':
    main()