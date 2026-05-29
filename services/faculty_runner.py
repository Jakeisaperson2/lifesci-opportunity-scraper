"""
Faculty runner — orchestrates Michigan Medicine faculty scraping and enrichment.

run_faculty_scrape()   — pulls NIH Reporter data, persists new FacultyMember records
run_tableau_enrichment() — pulls Tableau dashboard data, enriches matched records
                           with lab_assets, project_ideas, and lab website URL
"""
import difflib
import hashlib
import re
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy.orm import Session

from database.models import FacultyMember
from database.session import SessionLocal
from scrapers.base import FacultyData
from scrapers.um_faculty import UMFacultyScraper
from scrapers.tableau_faculty import TableauFacultyScraper


class _FakeSource:
    """Minimal object satisfying BaseScraper.__init__ without a DB row."""
    id = None
    name = "Michigan Medicine Faculty"
    url = "https://researchers.umich.edu"
    scraper_key = "um_faculty"


class _TableauSource:
    id = None
    name = "UM Faculty Tableau Dashboard"
    url = "https://tableau.dsc.umich.edu/t/UM-Public/views/FacultyDatabaseDashboard"
    scraper_key = "tableau_faculty"


# ---------------------------------------------------------------------------
# NIH Reporter scrape
# ---------------------------------------------------------------------------

def run_faculty_scrape() -> dict:
    """
    Scrape Michigan Medicine faculty from NIH Reporter and persist new records.
    Safe to call repeatedly — existing profiles are updated, not duplicated.
    Returns {"found": int, "new": int}.
    """
    db: Session = SessionLocal()
    try:
        return _run_nih(db)
    finally:
        db.close()


def _run_nih(db: Session) -> dict:
    logger.info("Starting Michigan Medicine faculty scrape (NIH Reporter)")
    scraper = UMFacultyScraper(_FakeSource())

    try:
        raw: list[FacultyData] = scraper.scrape()
    except Exception as e:
        logger.error(f"Faculty scraper raised unexpectedly: {e}")
        return {"found": 0, "new": 0}

    found = len(raw)
    new_count = 0

    for fac in raw:
        try:
            if not fac.name or not fac.profile_url:
                continue

            url_hash = hashlib.md5(fac.profile_url.strip().lower().encode()).hexdigest()
            exists = db.query(FacultyMember).filter(FacultyMember.url_hash == url_hash).first()

            if exists:
                exists.research_interests = fac.research_interests or exists.research_interests
                exists.title = fac.title or exists.title
                exists.last_updated = datetime.now(timezone.utc)
                db.commit()
                continue

            member = FacultyMember(
                name=fac.name[:255],
                title=(fac.title or "")[:255],
                department=(fac.department or "")[:255],
                school=(fac.school or "Michigan Medicine")[:255],
                research_interests=fac.research_interests or "",
                lab_assets="",
                project_ideas="",
                email=(fac.email or "")[:255],
                phone=(fac.phone or "")[:100],
                profile_url=fac.profile_url[:1000],
                url_hash=url_hash,
                raw_data=fac.raw_data or "",
            )
            db.add(member)
            db.commit()
            new_count += 1

        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to persist faculty '{fac.name[:60]}': {e}")

    logger.info(f"NIH faculty scrape complete: {found} found, {new_count} new")
    return {"found": found, "new": new_count}


# ---------------------------------------------------------------------------
# Tableau enrichment
# ---------------------------------------------------------------------------

def run_tableau_enrichment() -> dict:
    """
    Pull Tableau dashboard data and enrich matching FacultyMember records
    with lab_assets, project_ideas, and lab website URL.
    Unmatched rows are inserted as new records with the Tableau fields populated.
    Returns {"scraped": int, "matched": int, "new": int, "unmatched": int}.
    """
    db: Session = SessionLocal()
    try:
        return _run_tableau(db)
    finally:
        db.close()


def _run_tableau(db: Session) -> dict:
    logger.info("Starting Tableau faculty enrichment")
    scraper = TableauFacultyScraper(_TableauSource())

    try:
        tableau_rows: list[FacultyData] = scraper.scrape()
    except Exception as e:
        logger.error(f"Tableau scraper raised: {e}")
        return {"scraped": 0, "matched": 0, "new": 0, "unmatched": 0}

    if not tableau_rows:
        logger.warning("Tableau scraper returned no rows")
        return {"scraped": 0, "matched": 0, "new": 0, "unmatched": 0}

    # Build a lookup of existing faculty: normalized_name → FacultyMember
    all_members = db.query(FacultyMember).filter(FacultyMember.is_active == True).all()
    name_index: dict[str, FacultyMember] = {_normalize_name(m.name): m for m in all_members}

    matched = new_count = unmatched = 0

    for fac in tableau_rows:
        try:
            member = _find_match(fac.name, name_index)

            if member:
                # Enrich existing record
                if fac.lab_assets:
                    member.lab_assets = fac.lab_assets
                if fac.project_ideas:
                    member.project_ideas = fac.project_ideas
                # Prefer the lab website URL over the NIH Reporter profile link
                if fac.profile_url:
                    member.profile_url = fac.profile_url[:1000]
                # Fill in title/dept from Tableau if missing in NIH record
                if not member.title and fac.title:
                    member.title = fac.title[:255]
                if not member.department and fac.department:
                    member.department = fac.department[:255]
                member.last_updated = datetime.now(timezone.utc)
                db.commit()
                matched += 1

            else:
                # Insert as a new record if not found in NIH data
                logger.debug(f"Tableau unmatched (inserting new): {fac.name}")
                # Use lab URL if present; fall back to name so each person gets a unique hash
                dedup_key = fac.profile_url.strip() if fac.profile_url.strip() else f"__name__{fac.name.strip().lower()}"
                url_hash = hashlib.md5(dedup_key.encode()).hexdigest()

                existing_hash = db.query(FacultyMember).filter(
                    FacultyMember.url_hash == url_hash
                ).first()

                if not existing_hash:
                    member = FacultyMember(
                        name=fac.name[:255],
                        title=(fac.title or "")[:255],
                        department=(fac.department or "")[:255],
                        school="Michigan Medicine",
                        lab_assets=fac.lab_assets or "",
                        project_ideas=fac.project_ideas or "",
                        # Use None (not "") so UNIQUE constraint allows multiple no-URL records
                        profile_url=fac.profile_url.strip()[:1000] if fac.profile_url.strip() else None,
                        url_hash=url_hash,
                        raw_data='{"source":"tableau"}',
                    )
                    db.add(member)
                    db.commit()
                    new_count += 1
                    # Add to index so duplicates within same Tableau run don't re-insert
                    name_index[_normalize_name(fac.name)] = member
                else:
                    unmatched += 1

        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to enrich '{fac.name[:60]}': {e}")

    logger.info(
        f"Tableau enrichment complete: {len(tableau_rows)} scraped, "
        f"{matched} matched, {new_count} new, {unmatched} unmatched"
    )
    return {
        "scraped": len(tableau_rows),
        "matched": matched,
        "new": new_count,
        "unmatched": unmatched,
    }


# ---------------------------------------------------------------------------
# Name matching helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, remove single-letter tokens (middle initials)."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z\s]", "", name)
    return " ".join(t for t in name.split() if len(t) > 1)


def _find_match(tableau_name: str, index: dict[str, FacultyMember]):
    """
    Find the best-matching FacultyMember for a Tableau name.
    Strategy (in order):
      1. Exact normalized match
      2. Token-subset match (handles middle initials: "Adam S Helms" ↔ "Adam Helms")
      3. difflib similarity ≥ 0.85 (handles minor variations)
    """
    norm = _normalize_name(tableau_name)
    if not norm:
        return None

    # 1. Exact match
    if norm in index:
        return index[norm]

    tokens_t = set(norm.split())

    best_match = None
    best_ratio = 0.0

    for key, member in index.items():
        tokens_k = set(key.split())

        # 2. Token-subset match
        if tokens_t <= tokens_k or tokens_k <= tokens_t:
            return member

        # 3. Similarity fallback
        ratio = difflib.SequenceMatcher(None, norm, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = member

    if best_ratio >= 0.85:
        return best_match

    return None
