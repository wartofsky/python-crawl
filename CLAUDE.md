# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python web crawler that uses AI (crawl4ai + OpenAI) to extract staff directory information (names, roles, emails) from web pages with varying HTML structures. Uses a hybrid extraction strategy that auto-detects the best method (LLM vs Regex).

## Commands

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m crawl4ai.install  # Install Playwright/Chromium browser

# Run the crawler
source venv/bin/activate && python main.py
```

## Environment Variables

Requires `OPENAI_API_KEY` in `.env` file.

## Architecture

```
main.py              # Entry point - configures URL and runs crawler
staff_crawler.py     # StaffDirectoryCrawler class - core extraction logic
models.py            # Pydantic models: StaffMember, StaffDirectory
results/             # CSV output directory (auto-generated)
```

### Key Components

- **StaffDirectoryCrawler**: Main class using crawl4ai's `AsyncWebCrawler`
  - `extract(url)`: Single URL extraction with hybrid strategy
  - `extract_many(urls)`: Parallel extraction from multiple URLs
  - `extract_with_pagination(url, config)`: Handles multi-page directories
  - `to_csv(staff)`: Export results to timestamped CSV

- **Hybrid Extraction Strategy**:
  - **LLM (GPT-4o-mini)**: For pages where emails are visible in rendered content
  - **Regex patterns**: For pages with emails embedded in HTML (mailto:, aria-label, JSON)
  - Auto-detection based on email count in HTML vs markdown

- **Pagination Support**:
  - **URL-based**: Detects `?page=N`, `?page_no=N`, `?const_page=N` patterns
  - **JS-based**: Click on Next button with configurable selectors

### Data Flow

1. AsyncWebCrawler (Playwright) renders page including JS content
2. Analyze content type (embedded vs visible emails)
3. If embedded → use regex patterns (fast, no API cost)
4. If visible → use LLM extraction (flexible, context-aware)
5. For pagination: detect URL patterns or use JS click navigation
6. Results parsed into `List[StaffMember]`
7. Export to CSV in `results/`

### Key Regex Patterns

```python
# aria-label pattern (Baltimore CMS style)
r'aria-label="Send message to ([^"]+?) at ([email])"'

# mailto pattern with adjacent name
r'mailto:([email])[^>]*>([^<]+)</a>'

# JSON embedded data
r'"(?:email|mail)":\s*"([^"]+@[^"]+)"[^}]*"(?:name|title)":\s*"([^"]+)"'
```

## Dependencies

- **crawl4ai**: Web crawling with LLM integration (uses Playwright)
- **openai**: LLM API for intelligent extraction (GPT-4o-mini)
- **pydantic**: Data validation and schema generation
- **python-dotenv**: Environment variable management

## URLs Tested

| URL | Type | Strategy |
|-----|------|----------|
| generalstanford.nn.k12.va.us/faculty.html | Simple | Regex |
| aacps.org/o/marleyes/page/faculty-staff | Accordions | Regex |
| baltimorecityschools.org/o/ruhrah/staff | URL pagination (8 pages) | Hybrid |
| ovs.onslow.k12.nc.us/directory | URL pagination (3 pages) | LLM |
