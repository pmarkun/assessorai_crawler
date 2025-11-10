# AGENTS.md

## Testing Guidelines

When testing spiders, use `max_pages=1` to limit to the first page only, for faster execution.

Example: `scrapy crawl es-linhares -a ano=2020 -a max_pages=1`