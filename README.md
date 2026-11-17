# LifeSci Opportunity Scraper

**A business-development intelligence platform for academic medical centers.** It automatically discovers life sciences funding and partnership opportunities (grants, RFPs, clinical trials, SBIR solicitations), matches them against a searchable faculty research directory, and tracks every lead through a built-in CRM pipeline.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-38B2AC?logo=tailwindcss&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## The Problem

Research funding and industry-partnership opportunities are scattered across dozens of government portals, foundation sites, and RSS feeds. Business-development teams spend hours each week checking them by hand, then track follow-ups in spreadsheets. Good opportunities get missed, and nobody can easily see which faculty are the right fit.

## What It Does

| Capability | Details |
|---|---|
| **Automated discovery** | 6 pluggable scrapers pull from ClinicalTrials.gov, Grants.gov, NIH Guide, SBIR.gov, Wellcome Trust, and RWJF |
| **Classification** | Rule-based classifier tags each opportunity by type (grant, RFP, clinical trial, sponsored research…) and therapeutic area (oncology, neurology, AI/digital health…) |
| **Deduplication** | URL-hash dedup keeps results clean across repeated scrapes |
| **Faculty directory** | ~1,100 researcher profiles built from the NIH RePORTER API and enriched with lab assets and project ideas via fuzzy name matching |
| **CRM pipeline** | 10-stage pipeline (New → Reviewing → Outreach → Proposal → Submitted → Awarded) with organizations, contacts, activity logs, and tasks |
| **Dashboard** | Single-page web UI with 7 tabs, filters, inline status updates, and modal-based editing |

## Architecture

```
            ┌──────────────────────────────────────────────┐
            │      Web Dashboard (Tailwind + vanilla JS)    │
            └──────────────────────┬───────────────────────┘
                                   │ REST / JSON
            ┌──────────────────────▼───────────────────────┐
            │                FastAPI backend                │
            │  /opportunities  /faculty  /scrape  /crm/*    │
            └───────┬───────────────────────────┬──────────┘
                    │                           │
     ┌──────────────▼─────────────┐   ┌─────────▼──────────┐
     │ Services                   │   │ SQLAlchemy + SQLite │
     │ scrape → classify → dedup  │──▶│ opportunities, orgs,│
     │ → persist                  │   │ contacts, tasks,    │
     └──────────────┬─────────────┘   │ faculty, runs       │
                    │                 └─────────────────────┘
     ┌──────────────▼─────────────────────────────────────┐
     │ Scrapers (BaseScraper plugins, registered by key)   │
     │ REST APIs · RSS feeds · HTML / Next.js extraction   │
     └─────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/Jakeisaperson2/lifesci-opportunity-scraper.git
cd lifesci-opportunity-scraper

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # Windows: copy .env.example .env
python main.py
```

Open **http://127.0.0.1:8000**, then click **Run Scrape** to pull live opportunities. Interactive API docs are at **http://127.0.0.1:8000/docs**.

## Project Structure

```
lifesci-opportunity-scraper/
├── main.py                  # Entry point: init DB, seed sources, start server
├── config/sources.yaml      # Scraping targets (seeded into the DB on startup)
├── api/
│   ├── app.py               # FastAPI app and router registration
│   └── routes/              # opportunities, faculty, sources, scrape, crm/*
├── database/
│   ├── models.py            # ORM models
│   └── session.py           # Engine, sessions, lightweight auto-migrations
├── scrapers/                # One module per source + registry.py
├── services/                # Classifier, deduplicator, scrape & faculty runners
├── frontend/
│   ├── templates/index.html # Dashboard UI
│   └── static/app.js        # Tab-based SPA logic
└── utils/logger.py          # Loguru configuration
```

## Adding a New Data Source

1. Create `scrapers/my_source.py`, subclass `BaseScraper`, and implement `scrape()`.
2. Register it in `scrapers/registry.py`.
3. Add an entry to `config/sources.yaml` and restart the app.

## Roadmap

- [ ] Update ClinicalTrials.gov and NIH Guide scrapers for recent upstream API/URL changes
- [ ] AI summarization and opportunity-to-faculty matching with an LLM
- [ ] Scheduled auto-scraping (APScheduler)
- [ ] Email/Slack alerts for saved searches
- [ ] Playwright support for JavaScript-rendered partner portals
- [ ] CSV/Excel export and full-text search (SQLite FTS5)

## License

[MIT](LICENSE)
