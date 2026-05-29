# CLAUDE.md — LifeSci Opportunity Discovery Platform

Internal BD intelligence tool for an academic medical center. Automatically
scrapes life sciences and healthcare websites for collaboration opportunities:
RFPs, clinical trial partnerships, sponsored research, grants, and research
collaborations.

---

## Quick Start

```bash
# Activate virtual environment (already created, do not recreate)
.venv\Scripts\activate

# Start the server
py main.py
# → App available at http://127.0.0.1:8000
# → Click "Run Scrape" in the browser to pull live data
```

**Python note:** Use `py` not `python` — Python 3.9.10 is installed via the
Windows py launcher. The venv is at `.venv/` and all dependencies are already
installed.

---

## Project Structure

```
lifesci-opportunity-scraper/
│
├── main.py                   # Entry point: init DB, seed sources, start uvicorn
├── requirements.txt          # All dependencies (pinned)
├── .env / .env.example       # Environment variables (DB path, log level, etc.)
├── config/sources.yaml       # Seed data for source_sites DB table
│
├── api/
│   ├── app.py                # FastAPI app: mounts routes + static files
│   └── routes/
│       ├── opportunities.py  # GET /api/opportunities (search, filter, paginate)
│       ├── sources.py        # GET /api/sources, PUT /api/sources/{id}/toggle
│       └── scrape.py         # POST /api/scrape, GET /api/scrape/runs
│
├── database/
│   ├── models.py             # SQLAlchemy ORM: SourceSite, Opportunity, ScrapeRun
│   └── session.py            # engine, SessionLocal, get_db(), init_db()
│
├── scrapers/
│   ├── base.py               # BaseScraper ABC + OpportunityData dataclass
│   ├── registry.py           # Maps scraper_key string → scraper class
│   ├── clinicaltrials.py     # ClinicalTrials.gov REST API v2
│   ├── grants_gov.py         # Grants.gov REST API (POST-based search)
│   └── nih_guide.py          # NIH Guide RSS feed (FOAs: RFA, PAR, PA, RFP)
│
├── services/
│   ├── classifier.py         # Keyword rules → opportunity_type + therapeutic_area
│   ├── deduplicator.py       # URL-hash dedup; normalize_title for secondary check
│   └── scrape_runner.py      # Orchestrates: fetch → classify → dedup → persist
│
├── frontend/
│   ├── templates/index.html  # Tailwind dashboard (Jinja2 template)
│   └── static/app.js         # Vanilla JS: fetch API, filters, pagination, scrape btn
│
├── utils/
│   └── logger.py             # Loguru: console (colored) + rotating file log
│
├── data/                     # SQLite DB lives here (gitignored)
│   └── opportunities.db      # Created automatically on first run
│
└── logs/                     # Log files (gitignored)
    ├── app.log               # Rotating application log
    └── server.log            # Uvicorn stdout when launched via PowerShell
```

---

## Database Schema

**`source_sites`** — configured scraping targets (seeded from `config/sources.yaml`)
- `scraper_key` links to a class in `scrapers/registry.py`
- `enabled` can be toggled via PUT `/api/sources/{id}/toggle`
- `last_scraped` updated after each successful run

**`opportunities`** — discovered opportunities (deduplicated by `url_hash`)
- `url_hash` = MD5 of normalized URL — primary dedup key
- `title_normalized` = lowercased/stripped title — secondary dedup signal
- `opportunity_type`: grant, clinical_trial, rfp, collaboration, sponsored_research, pilot_study, data_partnership, other
- `therapeutic_area`: oncology, cardiology, neurology, rare_disease, ai_digital_health, immunology, infectious_disease, metabolic_endocrine, respiratory, ophthalmology

**`scrape_runs`** — one record per scraper execution (status: running/success/failed)

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dashboard HTML |
| GET | `/api/opportunities` | List with filters: `search`, `opportunity_type`, `therapeutic_area`, `days`, `page`, `limit` |
| GET | `/api/opportunities/{id}` | Single opportunity |
| POST | `/api/scrape` | Trigger background scrape (optional `?source_ids=1,2`) |
| GET | `/api/scrape/runs` | Recent scrape run history |
| GET | `/api/sources` | List all configured sources |
| PUT | `/api/sources/{id}/toggle` | Enable/disable a source |
| GET | `/health` | Health check |

---

## Active Scrapers

| Scraper | Key | Source | Method |
|---------|-----|--------|--------|
| `ClinicalTrialsScraper` | `clinicaltrials` | clinicaltrials.gov/api/v2 | REST API |
| `GrantsGovScraper` | `grants_gov` | apply07.grants.gov | POST REST API |
| `NIHGuideScraper` | `nih_guide` | grants.nih.gov/feeds/Guide.rss | RSS/XML |

---

## How to Add a New Scraper

1. **Create** `scrapers/my_source.py`:
   ```python
   from scrapers.base import BaseScraper, OpportunityData

   class MySourceScraper(BaseScraper):
       def scrape(self) -> list[OpportunityData]:
           # fetch, parse, return list of OpportunityData
           ...
   ```

2. **Register** in `scrapers/registry.py`:
   ```python
   from scrapers.my_source import MySourceScraper
   REGISTRY = {
       ...
       "my_key": MySourceScraper,
   }
   ```

3. **Add** to `config/sources.yaml`:
   ```yaml
   - name: My Source Name
     url: https://example.com/opportunities
     scraper_key: my_key
     enabled: true
     scrape_interval_hours: 24
   ```

4. Restart the app — the new source is seeded automatically on startup.

---

## Known Issues Fixed This Session

- **Python 3.9 type hint incompatibility**: `str | None` union syntax requires
  Python 3.10+. Fixed by replacing with `Optional[str]` from `typing` in
  `scrapers/base.py`, `scrapers/nih_guide.py`, and `services/scrape_runner.py`.

- **greenlet build failure on Python 3.9 Windows**: `greenlet` 3.x dropped
  pre-built Windows wheels for Python 3.9. Fixed by pinning `greenlet==2.0.2`
  in `requirements.txt`.

---

## Environment Variables (.env)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_PATH` | `data/opportunities.db` | SQLite file location |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FILE` | `logs/app.log` | Log file path |
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8000` | Server port |

---

## How to Start the Server (Windows)

**Simple (recommended):**
```bash
py main.py
```

**Detached background process via PowerShell** (if running from Claude Code):
```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "main.py" `
  -RedirectStandardOutput "logs\server.log" `
  -RedirectStandardError "logs\server_err.log" -NoNewWindow
```

**Stop the server:**
```powershell
Get-Process python | Stop-Process -Force
```

---

## Backlog / Next Steps

- [ ] Add more scrapers: BARDA, NSF, SBIR.gov, pharma company partnership pages
- [ ] Scheduled auto-scraping (APScheduler or Windows Task Scheduler)
- [ ] Email/Slack alerts for new opportunities matching saved filters
- [ ] AI summarization of opportunity descriptions (Claude API)
- [ ] CSV/Excel export from the dashboard
- [ ] Saved searches / watchlists per user
- [ ] Opportunity status tracking (interested / contacted / submitted / declined)
- [ ] Full-text search with ranking (SQLite FTS5)
- [ ] Playwright support for JS-rendered pages (pharma partner portals)

---

## GitHub

Repo: https://github.com/Jakeisaperson2/lifesci-opportunity-scraper (private)
Branch: `master`
