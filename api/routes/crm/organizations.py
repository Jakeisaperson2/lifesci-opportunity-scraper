from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database.session import get_db
from database.models import Organization

router = APIRouter(prefix="/crm/organizations", tags=["crm"])


class OrgIn(BaseModel):
    name: str
    org_type: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    relationship_status: Optional[str] = "prospect"
    last_contact_date: Optional[datetime] = None
    next_followup_date: Optional[datetime] = None


def _ser(org: Organization) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "org_type": org.org_type,
        "website": org.website,
        "notes": org.notes,
        "relationship_status": org.relationship_status,
        "last_contact_date": org.last_contact_date.isoformat() if org.last_contact_date else None,
        "next_followup_date": org.next_followup_date.isoformat() if org.next_followup_date else None,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "contact_count": len(org.contacts),
        "opportunity_count": len(org.opportunities),
    }


@router.get("")
def list_orgs(
    search: Optional[str] = Query(None),
    relationship_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Organization)
    if search:
        q = q.filter(Organization.name.ilike(f"%{search}%"))
    if relationship_status:
        q = q.filter(Organization.relationship_status == relationship_status)
    total = q.count()
    items = q.order_by(Organization.name).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "items": [_ser(o) for o in items],
    }


@router.post("")
def create_org(body: OrgIn, db: Session = Depends(get_db)):
    org = Organization(**body.dict())
    db.add(org)
    db.commit()
    db.refresh(org)
    return _ser(org)


@router.get("/{org_id}")
def get_org(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _ser(org)


@router.put("/{org_id}")
def update_org(org_id: int, body: OrgIn, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(org, k, v)
    db.commit()
    db.refresh(org)
    return _ser(org)


@router.delete("/{org_id}")
def delete_org(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    db.delete(org)
    db.commit()
    return {"deleted": True}
