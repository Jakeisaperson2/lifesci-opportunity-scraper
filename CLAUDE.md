# CLAUDE.md — FFMI Brain

Internal BD intelligence and CRM platform for Michigan Medicine. Automatically scrapes life
sciences websites for collaboration opportunities (RFPs, clinical trial partnerships,
sponsored research, grants), maintains a Michigan Medicine faculty directory, and provides
a full CRM pipeline for tracking organizations, contacts, activities, and business development tasks.

---

## Quick Start

```bash
# Activate virtual environment (already created, do not recreate)
.venv\Scripts\activate

# Start the server
py main.py
# → App available at http://127.0.0.1:8000
# → Click "Run Scrape" to pull live opportunity data
# → Click "Faculty Directory" tab → "Refresh Faculty" to refresh researcher profiles
```

**Python note:** Use `py` not `python` — Python 3.9.10 via the Windows py launcher.
The venv is at `.venv/` and all dependencies are installed.

---

## Project Structure

```
lifesci-opportunity-scraper/
│
├── main.py                     # Entry point: init_db, migrate_db, seed_sources, uvicorn
├── requirements.txt            # All dependencies (pinned)
├── .env / .env.example         # DB path, log level, host/port
├── config/sources.yaml         # Seed data for source_sites DB table
│
├── api/
│   ├── app.py                  # FastAPI app: mounts all routers + static files
│   └── routes/
│       ├── opportunities.py    # GET/PATCH /api/opportunities (search, filter, crm_status, paginate)
│       ├── sources.py          # GET /api/sources, PUT /api/sources/{id}/toggle
│       ├── scrape.py           # POST /api/scrape, GET /api/scrape/runs
│       ├── faculty.py          # GET/POST /api/faculty, /api/faculty/refresh, /api/faculty/enrich
│       └── crm/
│           ├── organizations.py  # CRUD /api/crm/organizations
│           ├── contacts.py       # CRUD /api/crm/contacts
│           ├── activities.py     # CRUD /api/crm/activities
│           ├── tasks.py          # CRUD /api/crm/tasks + PATCH status
│           └── pipeline.py       # GET /api/crm/pipeline (stage counts)
│
├── database/
│   ├── models.py               # ORM: SourceSite, Opportunity, Organization, Contact, Activity, Task, FacultyMember, ScrapeRun
│   └── session.py              # engine, SessionLocal, get_db(), init_db(), migrate_db()
│
├── scrapers/
│   ├── base.py                 # BaseScraper ABC + OpportunityData + FacultyData dataclasses
│   ├── registry.py             # Maps scraper_key → class
│   ├── clinicaltrials.py       # ClinicalTrials.gov REST API v2
│   ├── grants_gov.py           # Grants.gov REST API (POST-based search)
│   ├── nih_guide.py            # NIH Guide RSS feed
│   ├── sbir_gov.py             # SBIR.gov solicitations REST API
│   ├── wellcome.py             # Wellcome Trust (HTML + Next.js data extraction)
│   ├── rwjf.py                 # Robert Wood Johnson Foundation (HTML)
│   ├── um_faculty.py           # Michigan Medicine faculty via NIH Reporter API
│   └── tableau_faculty.py      # U-M Faculty Database Dashboard (Tableau CSV endpoint)
│
├── services/
│   ├── classifier.py           # Keyword rules → opportunity_type + therapeutic_area
│   ├── deduplicator.py         # URL hash dedup
│   ├── scrape_runner.py        # Orchestrates: fetch → classify → dedup → persist (opportunities)
│   └── faculty_runner.py       # run_faculty_scrape() + run_tableau_enrichment()
│
├── frontend/
│   ├── templates/index.html    # Tailwind dashboard — U-M branded (#00274C / #FFCB05)
│   └── static/app.js           # Vanilla JS: two-tab UI (Opportunities + Faculty Directory)
│
├── utils/logger.py             # Loguru setup (console + rotating file)
├── data/                       # SQLite DB (gitignored)
└── logs/                       # Log files (gitignored)
```

---

## Database Schema

### `source_sites`
Configured scraping targets seeded from `config/sources.yaml`.
- `scraper_key` links to `scrapers/registry.py`
- `enabled` togglable via PUT `/api/sources/{id}/toggle`

### `opportunities`
Deduplicated by `url_hash` (MD5 of normalized URL).
- `opportunity_type`: grant, clinical_trial, rfp, collaboration, sponsored_research, pilot_study, data_partnership, other
- `therapeutic_area`: oncology, cardiology, neurology, rare_disease, ai_digital_health, immunology, infectious_disease, metabolic_endocrine, respiratory, ophthalmology
- `crm_status`: new, reviewing, interested, outreach_started, proposal_in_progress, submitted, negotiating, awarded, lost, archived
- `organization_id` FK → organizations (nullable, for linking CRM org records)

### `organizations`
CRM organization records (pharma/biotech/academic partners).
- `relationship_status`: prospect, active, partner, inactive
- Linked to contacts, opportunities, activities

### `contacts`
Individual contacts at organizations.
- FK → organizations

### `activities`
Activity log entries (email, meeting, phone_call, proposal_submission, follow_up, internal_review, negotiation).
- FK → opportunities, organizations, contacts (all nullable)

### `tasks`
BD tasks with due dates and priorities (low/medium/high/urgent).
- `status`: open, in_progress, complete
- FK → opportunities (nullable)

### `faculty_members`
Michigan Medicine researcher directory. Deduplicated by `url_hash` of profile URL.
- `research_interests` — MeSH keyword terms from NIH Reporter grants
- `lab_assets` — lab/clinical capabilities from the U-M Tableau dashboard
- `project_ideas` — partnership project ideas from the Tableau dashboard
- `profile_url` — lab website URL (from Tableau) or NIH Reporter profile link

**Migration note:** `migrate_db()` is called on every startup and safely adds
`lab_assets` / `project_ideas` columns if missing (uses `PRAGMA table_info` + `ALTER TABLE`).

### `scrape_runs`
One record per scraper execution (status: running/success/failed).

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Dashboard HTML |
| GET | `/api/opportunities` | List with filters: `search`, `opportunity_type`, `therapeutic_area`, `crm_status`, `days`, `page`, `limit` |
| GET | `/api/opportunities/{id}` | Single opportunity |
| PATCH | `/api/opportunities/{id}/crm_status?status=…` | Update CRM pipeline status |
| PATCH | `/api/opportunities/{id}/organization?organization_id=…` | Link to org record |
| POST | `/api/scrape` | Trigger background scrape |
| GET | `/api/scrape/runs` | Recent scrape run history |
| GET | `/api/sources` | List all configured sources |
| PUT | `/api/sources/{id}/toggle` | Enable/disable a source |
| GET | `/api/faculty` | List faculty with filters |
| GET | `/api/faculty/departments` | Distinct department list |
| GET | `/api/faculty/{id}` | Single faculty member |
| POST | `/api/faculty/refresh` | NIH Reporter scrape + Tableau enrichment |
| POST | `/api/faculty/enrich` | Tableau enrichment only |
| **GET** | **`/api/crm/pipeline`** | **Pipeline stage counts** |
| **GET/POST** | **`/api/crm/organizations`** | **List / create organizations** |
| **GET/PUT/DELETE** | **`/api/crm/organizations/{id}`** | **Get / update / delete org** |
| **GET/POST** | **`/api/crm/contacts`** | **List / create contacts** |
| **GET/PUT/DELETE** | **`/api/crm/contacts/{id}`** | **Get / update / delete contact** |
| **GET/POST** | **`/api/crm/activities`** | **List / log activities** |
| **GET/PUT/DELETE** | **`/api/crm/activities/{id}`** | **Get / update / delete activity** |
| **GET/POST** | **`/api/crm/tasks`** | **List / create tasks** |
| **GET/PUT/DELETE** | **`/api/crm/tasks/{id}`** | **Get / update / delete task** |
| **PATCH** | **`/api/crm/tasks/{id}/status?status=…`** | **Toggle task status** |
| GET | `/health` | Health check |

---

## Active Opportunity Scrapers

| Scraper | Key | Source | Method |
|---------|-----|--------|--------|
| `ClinicalTrialsScraper` | `clinicaltrials` | clinicaltrials.gov/api/v2 | REST API |
| `GrantsGovScraper` | `grants_gov` | apply07.grants.gov | POST REST API |
| `NIHGuideScraper` | `nih_guide` | grants.nih.gov/feeds/Guide.rss | RSS/XML |
| `SBIRGovScraper` | `sbir_gov` | api.sbir.gov/public/api/solicitations | REST API |
| `WellcomeTrustScraper` | `wellcome` | wellcome.org/grant-funding | HTML/Next.js |
| `RWJFScraper` | `rwjf` | rwjf.org/grants/funding-opportunities | HTML |

---

## Faculty Directory Sources

### 1. NIH Reporter (`scrapers/um_faculty.py`)
- API: `POST https://api.reporter.nih.gov/v2/projects/search`
- Queries fiscal years 2024–2025 for `UNIVERSITY OF MICHIGAN AT ANN ARBOR`
- Filters to medicine-relevant departments (Internal Medicine, Oncology, etc.)
- Deduplicates by PI `profile_id` across grants; accumulates MeSH terms as `research_interests`
- Produces ~1,128 faculty records

### 2. U-M Tableau Dashboard (`scrapers/tableau_faculty.py`)
- URL: `https://tableau.dsc.umich.edu/t/UM-Public/views/FacultyDatabaseDashboard/Page2.csv?:showVizHome=no&:embed=y`
- No auth needed — guest access CSV endpoint works directly with `requests`
- 87–88 rows; columns: `Faculty Info` (name/dept/title), `Assets, Project Ideas, & Keywords` (sectioned text), `Lab Website`
- Parsed into `lab_assets` (LAB ASSETS + CLINICAL ASSETS sections) and `project_ideas`

### Enrichment / Name Matching (`services/faculty_runner.py`)
- `run_tableau_enrichment()` matches Tableau rows to existing NIH records by name
- Match strategy: exact normalized → token-subset (handles "Adam Helms" ↔ "Adam S Helms") → `difflib` similarity ≥ 0.85
- Matched: updates `lab_assets`, `project_ideas`, `profile_url` on existing record
- Unmatched: inserted as new record (clinical faculty not in NIH Reporter)
- Empty `profile_url` stored as `None` (not `""`) to avoid UNIQUE constraint collisions

---

## Frontend

Single-page app with two tabs: **Opportunities** and **Faculty Directory**.

**Branding:** U-M Blue `#00274C` header, Maize `#FFCB05` accents (buttons, subtitle, "Showing" stat).

**Opportunities tab:**
- Filters: text search, type, therapeutic area, time window
- Columns: Title/Description, Organization, Type (badge), Therapeutic Area (badge), Funding (green), Deadline (color-coded), Discovered, Source
- Funding column (`funding_amount`) shown in green

**Faculty Directory tab:**
- Lazy-loads on first tab visit
- Filters: text search (name/dept/interests/lab assets), department dropdown, "BD Profile Only" checkbox (`has_lab_data=true`)
- Columns: Name (linked), Title, Department, Research Interests (truncated), Lab Assets (truncated + hover tooltip), Contact
- Rows with Tableau BD data have a green dot indicator and subtle blue tint
- "Refresh Faculty" runs NIH Reporter scrape then Tableau enrichment sequentially

---

## How to Add a New Opportunity Scraper

1. Create `scrapers/my_source.py` inheriting `BaseScraper`, implement `scrape() -> list[OpportunityData]`
2. Add `"my_key": MySourceScraper` to `scrapers/registry.py`
3. Add entry to `config/sources.yaml` with `scraper_key: my_key`
4. Restart app — sources are seeded from YAML on startup

---

## Known Issues Fixed

- **Python 3.9 type hints**: `str | None` → `Optional[str]` in base.py, nih_guide.py, scrape_runner.py
- **greenlet build failure on Python 3.9 Windows**: pinned `greenlet==2.0.2`
- **Tableau guest CSV**: direct `.csv?:embed=y` endpoint works; `tableauscraper` library not needed
- **UNIQUE constraint on empty profile_url**: Tableau-only faculty with no lab website stored with `profile_url=None`
- **migrate_db()**: needed because `create_all()` won't add columns to existing tables

---

## Environment Variables (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DB_PATH` | `data/opportunities.db` | SQLite file location |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FILE` | `logs/app.log` | Log file path |
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8000` | Server port |

---

## How to Start the Server (Windows)

```bash
py main.py
```

**Stop:**
```powershell
Get-Process python | Stop-Process -Force
```

---

## Backlog / Next Steps

- [ ] Scheduled auto-scraping (APScheduler or Windows Task Scheduler)
- [ ] Email/Slack alerts for new opportunities matching saved filters
- [ ] AI summarization of opportunity descriptions (Claude API)
- [ ] CSV/Excel export from the dashboard
- [ ] Saved searches / watchlists per user
- [ ] Opportunity status tracking (interested / contacted / submitted / declined)
- [ ] Full-text search with ranking (SQLite FTS5)
- [ ] Playwright support for JS-rendered pages (pharma partner portals)
- [ ] Fix/update ClinicalTrials.gov and NIH Guide scrapers (currently returning 400/404 errors — API changes)
- [ ] Faculty: add cross-reference view linking opportunities to matching faculty by keyword overlap
- [ ] Faculty: scheduled auto-refresh (NIH Reporter + Tableau) via APScheduler

---

## GitHub

Repo: https://github.com/Jakeisaperson2/lifesci-opportunity-scraper (private)
Branch: `master`
