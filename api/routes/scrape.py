import threading
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import ScrapeRun

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("")
def trigger_scrape(
    background_tasks: BackgroundTasks,
    source_ids: Optional[str] = Query(None, description="Comma-separated source IDs, or omit for all"),
):
    """
    Trigger a scrape run in the background.
    Returns immediately — poll /api/scrape/runs to see status.
    """
    ids = None
    if source_ids:
        try:
            ids = [int(x.strip()) for x in source_ids.split(",")]
        except ValueError:
            pass

    # Import here to avoid circular imports at module load time
    from services.scrape_runner import run_all
    background_tasks.add_task(run_all, ids)

    return {"status": "started", "source_ids": ids or "all"}


@router.get("/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    runs = (
        db.query(ScrapeRun)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize(r) for r in runs]


def _serialize(r: ScrapeRun) -> dict:
    return {
        "id": r.id,
        "source_name": r.source.name if r.source else "All",
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "status": r.status,
        "opportunities_found": r.opportunities_found,
        "opportunities_new": r.opportunities_new,
        "error_message": r.error_message,
    }
