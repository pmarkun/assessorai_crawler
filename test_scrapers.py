#!/usr/bin/env python3
"""
Generic testing script for scrapers.
Runs each spider with a limit, validates output, and checks pipeline results.
"""

import argparse
import os
import sys
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any


def get_all_spiders() -> List[str]:
    """Get list of all available spiders via scrapy list."""
    try:
        result = subprocess.run([sys.executable, '-m', 'scrapy', 'list'],
                               capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        else:
            print(f"Error getting spiders: {result.stderr}")
            return []
    except Exception as e:
        print(f"Failed to get spiders: {e}")
        return []


def validate_item(item: Dict[str, Any]) -> List[str]:
    """Validate a single item against expected schema."""
    errors = []

    # Required fields
    required = ['title', 'house', 'full_text', 'url']
    for field in required:
        if field not in item or not item[field]:
            errors.append(f"Missing or empty required field: {field}")

    # Type checks
    if 'title' in item and not isinstance(item['title'], str):
        errors.append("title must be string")
    if 'house' in item and not isinstance(item['house'], str):
        errors.append("house must be string")
    if 'full_text' in item and not isinstance(item['full_text'], str):
        errors.append("full_text must be string")
    if 'number' in item and item['number'] is not None and not isinstance(item['number'], int):
        errors.append("number must be int or None")
    if 'year' in item and item['year'] is not None and not isinstance(item['year'], int):
        errors.append("year must be int or None")
    if 'length' in item and not isinstance(item['length'], int):
        errors.append("length must be int")
    if 'author' in item and not isinstance(item['author'], list):
        errors.append("author must be list")

    # Data quality
    if 'full_text' in item and len(item['full_text']) < 10:
        errors.append("full_text too short (<10 chars)")
    if 'uuid' in item and len(item['uuid']) != 32:
        errors.append("uuid invalid length")
    if 'scraped_at' in item:
        try:
            datetime.fromisoformat(item['scraped_at'])
        except ValueError:
            errors.append("scraped_at not valid ISO datetime")

    return errors


def check_md_files(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check if .md files exist for items with caminho_arquivo_texto."""
    results = {'total': len(items), 'with_md_path': 0, 'md_exists': 0, 'md_missing': 0}
    for item in items:
        path = item.get('caminho_arquivo_texto')
        if path:
            results['with_md_path'] += 1
            full_path = os.path.join('storage', 'downloads', 'md', path)
            if os.path.exists(full_path):
                results['md_exists'] += 1
            else:
                results['md_missing'] += 1
    return results


def test_spider(spider_name: str) -> Dict[str, Any]:
    """Test a single spider by running it and parsing output."""
    result = {
        'spider': spider_name,
        'status': 'UNKNOWN',
        'items_count': 0,
        'errors': [],
        'md_check': {},
        'sample_item': None
    }

    # Run scrapy crawl with limit
    cmd = [sys.executable, '-m', 'scrapy', 'crawl', spider_name, '-s', 'CLOSESPIDER_ITEMCOUNT=5', '-L', 'ERROR']
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd='.', timeout=300)  # 5 min timeout
        if proc.returncode != 0:
            result['status'] = 'CRAWL_FAILED'
            result['errors'].append(f"Crawl failed: {proc.stderr}")
            return result
    except subprocess.TimeoutExpired:
        result['status'] = 'TIMEOUT'
        result['errors'].append("Crawl timed out")
        return result
    except Exception as e:
        result['status'] = 'ERROR'
        result['errors'].append(f"Unexpected error: {str(e)}")
        return result

    # Read the JSON output file
    output_file = f'output/{spider_name}_proposicoes.json'
    if not os.path.exists(output_file):
        result['status'] = 'NO_OUTPUT'
        result['errors'].append(f"Output file not found: {output_file}")
        return result

    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except Exception as e:
        result['status'] = 'PARSE_ERROR'
        result['errors'].append(f"Failed to parse output: {str(e)}")
        return result

    result['items_count'] = len(items)

    if not items:
        result['status'] = 'NO_ITEMS'
        result['errors'].append("No items in output")
        return result

    # Validate items
    validation_errors = []
    for i, item in enumerate(items):
        item_errors = validate_item(item)
        if item_errors:
            validation_errors.extend([f"Item {i}: {err}" for err in item_errors])

    if validation_errors:
        result['errors'].extend(validation_errors)
        result['status'] = 'VALIDATION_FAILED'
    else:
        result['status'] = 'PASSED'

    # Check .md files
    result['md_check'] = check_md_files(items)

    # Sample item (first one)
    if items:
        result['sample_item'] = items[0]

    # Clean up output file
    try:
        os.remove(output_file)
    except:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description="Test scrapers generically")
    parser.add_argument('--spiders', help="Comma-separated spider names (e.g., es-linhares,ce-fortaleza)")
    parser.add_argument('--all', action='store_true', help="Test all spiders")
    parser.add_argument('--output', help="Output JSON file")
    args = parser.parse_args()

    if args.all:
        spiders = get_all_spiders()
    elif args.spiders:
        spiders = [s.strip() for s in args.spiders.split(',')]
    else:
        print("Use --spiders or --all")
        sys.exit(1)

    print(f"Testing {len(spiders)} spiders: {', '.join(spiders)}")

    results = []
    for spider in spiders:
        print(f"Testing {spider}...")
        result = test_spider(spider)
        results.append(result)
        status = result['status']
        count = result['items_count']
        print(f"  {spider}: {status} ({count} items)")

    # Summary
    passed = sum(1 for r in results if r['status'] == 'PASSED')
    total = len(results)
    print(f"\nSummary: {passed}/{total} passed")

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.output}")
    else:
        # Print failed ones
        failed = [r for r in results if r['status'] != 'PASSED']
        if failed:
            print("\nFailed spiders:")
            for r in failed:
                print(f"  {r['spider']}: {r['status']} - {r['errors']}")


if __name__ == '__main__':
    main()