from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.session import get_db
from database.models import Activity

router = APIRouter(prefix="/crm/activities", tags=["crm"])


class ActivityIn(BaseModel):
    date: Optional[datetime] = None
    activity_type: str
    description: Optional[str] = None
    opportunity_id: Optional[int] = None
    organization_id: Optional[int] = None
    contact_id: Optional[int] = None


def _ser(a: Activity) -> dict:
    return {
        "id": a.id,
        "date": a.date.isoformat() if a.date else None,
        "activity_type": a.activity_type,
        "description": a.description,
        "opportunity_id": a.opportunity_id,
        "opportunity_title": a.opportunity.title if a.opportunity else None,
        "organization_id": a.organization_id,
        "organization_name": a.organization.name if a.organization else None,
        "contact_id": a.contact_id,
        "contact_name": a.contact.name if a.contact else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("")
def list_activities(
    opportunity_id: Optional[int] = Query(None),
    organization_id: Optional[int] = Query(None),
    activity_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Activity)
    if opportunity_id:
        q = q.filter(Activity.opportunity_id == opportunity_id)
    if organization_id:
        q = q.filter(Activity.organization_id == organization_id)
    if activity_type:
        q = q.filter(Activity.activity_type == activity_type)
    total = q.count()
    items = q.order_by(Activity.date.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "items": [_ser(a) for a in items],
    }


@router.post("")
def create_activity(body: ActivityIn, db: Session = Depends(get_db)):
    data = body.dict()
    if not data.get("date"):
        data["date"] = datetime.now(timezone.utc)
    a = Activity(**data)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _ser(a)


@router.get("/{activity_id}")
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    a = db.query(Activity).filter(Activity.id == activity_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _ser(a)


@router.put("/{activity_id}")
def update_activity(activity_id: int, body: ActivityIn, db: Session = Depends(get_db)):
    a = db.query(Activity).filter(Activity.id == activity_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Activity not found")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _ser(a)


@router.delete("/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    a = db.query(Activity).filter(Activity.id == activity_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(a)
    db.commit()
    return {"deleted": True}
