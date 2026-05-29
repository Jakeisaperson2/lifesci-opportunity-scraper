# LifeSci Opportunity Scraper

A Python application that scrapes the web for life sciences and healthcare funding and collaboration opportunities, including:

- **RFPs** (Requests for Proposals) from pharma and biotech companies
- **Sponsored research agreements** and industry-academia collaboration calls
- **Clinical trial partnerships** and CRO/site recruitment opportunities
- **Research grants and co-development calls** from life sciences organizations

## Overview

This MVP is a local Python scraper targeting publicly available opportunity listings from company websites, industry portals, and government databases. Results are stored locally for review and export.

## Project Structure

```
lifesci-opportunity-scraper/
├── scraper/          # Core scraping modules
│   ├── __init__.py
│   └── base.py       # Base scraper class
├── parsers/          # Site-specific HTML/data parsers
│   └── __init__.py
├── storage/          # Local data persistence
│   └── __init__.py
├── data/             # Output data (gitignored)
├── config/           # Configuration files
│   └── sources.yaml  # List of target URLs and scraping rules
├── requirements.txt
├── .env.example      # Template for environment variables
└── main.py           # Entry point
```

## Setup

```bash
# Clone the repo
git clone https://github.com/Jakeisaperson2/lifesci-opportunity-scraper.git
cd lifesci-opportunity-scraper

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
```

## Usage

```bash
python main.py
```

## Configuration

Edit `config/sources.yaml` to add or modify scraping targets. Each source entry specifies the URL, opportunity type, and parsing strategy.

## Data Sources (Planned)

- NIH Grants & Contracts (grants.nih.gov)
- ClinicalTrials.gov partnership listings
- Pharmaceutical company pipeline/partnering pages
- BIO (Biotechnology Innovation Organization) portal
- Industry-specific RFP aggregators

## License

Private — all rights reserved.
