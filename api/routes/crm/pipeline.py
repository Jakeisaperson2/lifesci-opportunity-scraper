from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.session import get_db
from database.models import Opportunity

router = APIRouter(prefix="/crm/pipeline", tags=["crm"])

STAGES = [
    ("new",                  "New"),
    ("reviewing",            "Reviewing"),
    ("interested",           "Interested"),
    ("outreach_started",     "Outreach Started"),
    ("proposal_in_progress", "Proposal Dev"),
    ("submitted",            "Submitted"),
    ("negotiating",          "Negotiating"),
    ("awarded",              "Awarded"),
    ("lost",                 "Lost"),
    ("archived",             "Archived"),
]


@router.get("")
def get_pipeline(db: Session = Depends(get_db)):
    counts = (
        db.query(Opportunity.crm_status, func.count(Opportunity.id))
        .filter(Opportunity.is_active == True)
        .group_by(Opportunity.crm_status)
        .all()
    )
    count_map = {status: cnt for status, cnt in counts}

    stages = []
    for key, label in STAGES:
        stages.append({
            "key": key,
            "label": label,
            "count": count_map.get(key, 0),
        })

    return {
        "stages": stages,
        "total": sum(s["count"] for s in stages),
    }
