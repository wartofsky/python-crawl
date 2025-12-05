# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python web crawler that uses AI (crawl4ai + OpenAI) to extract staff directory information (names, roles, emails) from web pages with varying HTML structures.

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

- **StaffDirectoryCrawler**: Main class using crawl4ai's `AsyncWebCrawler` with `LLMExtractionStrategy`
  - `extract(url)`: Single URL extraction
  - `extract_many(urls)`: Parallel extraction from multiple URLs
  - `to_csv(staff)`: Export results to timestamped CSV

- **LLMExtractionStrategy**: Uses OpenAI GPT-5-nano with Pydantic schema to intelligently parse HTML regardless of structure
  - Hybrid extraction: auto-detects if data is embedded in HTML (uses regex) or visible (uses LLM)
  - `extract_with_pagination(url)`: Handles multi-page directories with Next button

### Data Flow

1. AsyncWebCrawler (Playwright) renders page including JS content
2. LLMExtractionStrategy sends HTML to OpenAI with schema
3. Response parsed into `List[StaffMember]`
4. Results exported to CSV in `results/`

## Dependencies

- **crawl4ai**: Web crawling with LLM integration (uses Playwright)
- **openai**: LLM API for intelligent extraction
- **pydantic**: Data validation and schema generation
- **python-dotenv**: Environment variable management
