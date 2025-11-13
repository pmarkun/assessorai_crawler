#!/usr/bin/env python3
"""
Simple Scraper for João Pessoa PB Legislative Proposals

This script scrapes legislative proposals from the João Pessoa PB municipal chamber's SAPL-based system.
It processes the specified page of a proposals list, extracts metadata for each proposal, and prints the results.

Usage:
    python pb-joao-pessoa.py --page 1 --ano 2025

Arguments:
- --page: Page number to scrape (default: 1)
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

def extract_metadata_from_row(row, domain):
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

    # The entire content is in one <td>
    td = row.cssselect('td')
    if not td:
        return None
    content = td[0]

    # Extract title from the first <strong><a>
    title_link = content.cssselect('strong a')
    if not title_link:
        return None
    title_text = title_link[0].text_content().strip()
    link_detalhes_relativo = title_link[0].get('href', '')

    # Parse title to extract type, number, year (e.g., "VETO 1/2025 - Veto")
    match_titulo = re.search(r'(\w+)\s+(\d+)/(\d{4})\s+-\s+(.*)', title_text)
    if match_titulo:
        item['number'] = str(match_titulo.group(2))
        item['year'] = str(match_titulo.group(3))
        item['type'] = match_titulo.group(4).strip()
        item['title'] = f"{item['type']} nº {item['number']}/{item['year']}"
    else:
        item['title'] = title_text
        item['number'] = None
        item['year'] = None
        item['type'] = None

    # Extract subject from Ementa
    ementa_div = content.xpath('.//strong[contains(text(), "Ementa:")]/following-sibling::div[@class="dont-break-out"]')
    item['subject'] = ementa_div[0].text_content().strip() if ementa_div else ''

    # Extract presentation date
    presentation_text = content.xpath('string(.//strong[contains(text(), "Apresentação:")]/following-sibling::text()[1])')
    item['presentation_date'] = presentation_text.strip() if presentation_text else ''

    # Extract author
    author_text = content.xpath('string(.//strong[contains(text(), "Autor:")]/following-sibling::text()[1])')
    item['author'] = [author_text.strip()] if author_text else []

    # Extract relatorias (reports)
    relatorias_text = content.xpath('string(.//strong[contains(text(), "Relatorias:")]/following-sibling::text()[1])')
    item['relatorias'] = relatorias_text.strip() if relatorias_text else ''

    # Extract current location
    location_text = content.xpath('string(.//strong[contains(text(), "Localização Atual:")]/following-sibling::text()[1])')
    item['current_location'] = location_text.strip() if location_text else ''

    # Extract status
    status_text = content.xpath('string(.//strong[contains(text(), "Status:")]/following-sibling::text()[1])')
    item['status'] = status_text.strip() if status_text else ''

    # Extract result
    result_text = content.xpath('string(.//strong[contains(text(), "Resultado:")]/following-sibling::text()[1])')
    item['result'] = result_text.strip() if result_text else ''

    # Extract voting dates (multiple possible)
    voting_dates = content.xpath('.//strong[contains(text(), "Data Votação:")]/following-sibling::div//a/text()')
    item['voting_dates'] = [date.strip() for date in voting_dates] if voting_dates else []

    # Extract last action
    last_action_text = content.xpath('string(.//strong[contains(text(), "Última Ação:")]/following-sibling::text()[1])')
    item['last_action'] = last_action_text.strip() if last_action_text else ''

    # Extract PDF URL from "Texto Original"
    pdf_link = content.xpath('.//strong/a[contains(text(), "Texto Original")]/@href')
    if pdf_link:
        pdf_relative_url = pdf_link[0]
        item['url'] = domain + pdf_relative_url
        item['file_urls'] = [item['url']]

    # Set fixed fields for João Pessoa PB
    item['house'] = 'Câmara Municipal de João Pessoa'
    item['scraped_at'] = datetime.now().isoformat()

    # Generate unique ID based on project URL
    item['uuid'] = hashlib.md5((domain + link_detalhes_relativo).encode('utf-8')).hexdigest()
    item['project_url'] = domain + link_detalhes_relativo

    # Generate path for markdown file
    uf = 'PB'
    slug = 'pb-joao-pessoa'
    normalized_type = item['type'].lower().replace(' ', '-').replace('à', 'a') if item['type'] else 'unknown'
    item['md_files'] = f"{uf}/{slug}/{normalized_type}-{item['number']}-{item['year']}.md"

    return item

def main():
    """
    Main function to run the scraper.

    Parses command-line arguments, builds the URL, fetches the page, extracts proposals,
    finds pagination info, and prints the results.
    """
    parser = argparse.ArgumentParser(description='Simple scraper for João Pessoa PB legislative proposals')
    parser.add_argument('--page', type=int, default=1, help='Page number to scrape (default: 1)')
    parser.add_argument('--ano', type=int, help='Year to filter proposals (optional)')
    args = parser.parse_args()

    # Build the URL
    domain = "https://sapl.joaopessoa.pb.leg.br"
    base_url = f"{domain}/materia/pesquisar-materia"
    url = f"{base_url}?page={args.page}"
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
        item = extract_metadata_from_row(linha, domain)
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
            next_page_url = domain + href if href.startswith('/materia') else (base_url + href if href.startswith('?') else href)
            print(f"DEBUG: Next page URL: {next_page_url}")

    # Extract total pages from pagination (last page number)
    total_pages = None
    page_links = tree.cssselect('ul.pagination li a.page-link')
    if page_links:
        # Get the last numeric page link
        for link in reversed(page_links):
            text = link.text_content().strip()
            if text.isdigit():
                total_pages = int(text)
                break
    if total_pages:
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