from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import SourceSite

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(SourceSite).order_by(SourceSite.name).all()
    return [_serialize(s) for s in sources]


@router.put("/{source_id}/toggle")
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(SourceSite).filter(SourceSite.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.enabled = not source.enabled
    db.commit()
    return _serialize(source)


def _serialize(s: SourceSite) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "url": s.url,
        "scraper_key": s.scraper_key,
        "enabled": s.enabled,
        "last_scraped": s.last_scraped.isoformat() if s.last_scraped else None,
        "scrape_interval_hours": s.scrape_interval_hours,
    }
