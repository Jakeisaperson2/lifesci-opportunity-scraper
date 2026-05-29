"""
Entry point for the LifeSci Opportunity Discovery platform.

Run with:
    py main.py               (uses HOST/PORT from .env, default 127.0.0.1:8000)
    uvicorn api.app:app --reload   (for development with auto-reload)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from utils.logger import setup_logging
setup_logging()

from loguru import logger
from database.session import init_db, migrate_db
from database.session import SessionLocal
from database.models import SourceSite


def seed_sources():
    """Insert source sites from config/sources.yaml if they don't already exist."""
    import yaml

    config_path = Path("config/sources.yaml")
    if not config_path.exists():
        logger.warning("config/sources.yaml not found — no sources seeded")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    db = SessionLocal()
    try:
        added = 0
        for s in sources:
            exists = db.query(SourceSite).filter(SourceSite.name == s["name"]).first()
            if not exists:
                db.add(SourceSite(
                    name=s["name"],
                    url=s["url"],
                    scraper_key=s["scraper_key"],
                    enabled=s.get("enabled", True),
                    scrape_interval_hours=s.get("scrape_interval_hours", 24),
                ))
                added += 1
        db.commit()
        if added:
            logger.info(f"Seeded {added} new source site(s)")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    logger.info("Initializing database...")
    init_db()
    migrate_db()
    seed_sources()

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting server at http://{host}:{port}")
    uvicorn.run("api.app:app", host=host, port=port, reload=False)
