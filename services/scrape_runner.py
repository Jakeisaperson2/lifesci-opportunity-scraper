"""
Scrape runner — orchestrates a full scraping cycle.

Flow for each enabled source:
  1. Create a ScrapeRun record (status=running)
  2. Look up the scraper class from the registry
  3. Call scraper.scrape() to get raw OpportunityData list
  4. Classify each opportunity (type + therapeutic area)
  5. Deduplicate against existing DB records
  6. Persist new opportunities
  7. Update the ScrapeRun record (status=success/failed)
  8. Update SourceSite.last_scraped
"""
from datetime import datetime, timezone
from typing import Optional
from loguru import logger
from sqlalchemy.orm import Session

from database.models import Opportunity, ScrapeRun, SourceSite
from database.session import SessionLocal
from scrapers.registry import get_scraper
from scrapers.base import OpportunityData
from services.classifier import classify
from services.deduplicator import is_duplicate, prepare_hashes


def run_all(source_ids: Optional[list] = None):
    """
    Run scrapers for all enabled sources, or a specific subset by ID.
    Called from the API endpoint (in a background thread) or CLI.
    """
    db: Session = SessionLocal()
    try:
        query = db.query(SourceSite).filter(SourceSite.enabled == True)
        if source_ids:
            query = query.filter(SourceSite.id.in_(source_ids))
        sources = query.all()

        if not sources:
            logger.warning("No enabled sources found — nothing to scrape")
            return

        for source in sources:
            _run_source(source, db)
    finally:
        db.close()


def _run_source(source: SourceSite, db: Session):
    run = ScrapeRun(source_site_id=source.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(f"Scraping: {source.name} (scraper_key={source.scraper_key})")

    scraper = get_scraper(source.scraper_key, source)
    if scraper is None:
        _fail_run(run, db, f"Unknown scraper_key: {source.scraper_key}")
        return

    try:
        raw_results: list[OpportunityData] = scraper.scrape()
    except Exception as e:
        _fail_run(run, db, str(e))
        logger.error(f"Scraper {source.scraper_key} raised: {e}")
        return

    found = len(raw_results)
    new_count = 0

    for opp_data in raw_results:
        try:
            if is_duplicate(opp_data, db):
                continue

            classify(opp_data)
            url_h, title_norm = prepare_hashes(opp_data)

            opp = Opportunity(
                title=opp_data.title[:500],
                title_normalized=title_norm[:500],
                description=opp_data.description,
                company_name=opp_data.company_name,
                opportunity_type=opp_data.opportunity_type,
                therapeutic_area=opp_data.therapeutic_area,
                funding_amount=opp_data.funding_amount,
                deadline=opp_data.deadline,
                url=opp_data.url[:1000],
                url_hash=url_h,
                contact_info=opp_data.contact_info,
                raw_data=opp_data.raw_data,
                source_site_id=source.id,
            )
            db.add(opp)
            db.commit()
            new_count += 1
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to persist opportunity '{opp_data.title[:60]}': {e}")

    now = datetime.now(timezone.utc)
    run.status = "success"
    run.completed_at = now
    run.opportunities_found = found
    run.opportunities_new = new_count
    source.last_scraped = now
    db.commit()

    logger.info(f"  → {source.name}: {found} found, {new_count} new")


def _fail_run(run: ScrapeRun, db: Session, message: str):
    run.status = "failed"
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = message[:2000]
    db.commit()
