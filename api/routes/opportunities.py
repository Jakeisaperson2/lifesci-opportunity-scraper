from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.session import get_db
from database.models import Opportunity

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("")
def list_opportunities(
    search: Optional[str] = Query(None),
    opportunity_type: Optional[str] = Query(None),
    therapeutic_area: Optional[str] = Query(None),
    crm_status: Optional[str] = Query(None),
    days: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Opportunity).filter(Opportunity.is_active == True)

    if search:
        like = f"%{search}%"
        query = query.filter(or_(
            Opportunity.title.ilike(like),
            Opportunity.description.ilike(like),
            Opportunity.company_name.ilike(like),
        ))

    if opportunity_type:
        query = query.filter(Opportunity.opportunity_type == opportunity_type)

    if therapeutic_area:
        query = query.filter(Opportunity.therapeutic_area.ilike(f"%{therapeutic_area}%"))

    if crm_status:
        query = query.filter(Opportunity.crm_status == crm_status)

    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(Opportunity.date_discovered >= cutoff)

    total = query.count()
    items = (
        query.order_by(Opportunity.date_discovered.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "items": [_serialize(o) for o in items],
    }


@router.get("/{opp_id}")
def get_opportunity(opp_id: int, db: Session = Depends(get_db)):
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _serialize(opp)


@router.patch("/{opp_id}/crm_status")
def update_crm_status(
    opp_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.crm_status = status
    db.commit()
    return _serialize(opp)


@router.patch("/{opp_id}/organization")
def link_organization(
    opp_id: int,
    organization_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    opp = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.organization_id = organization_id
    db.commit()
    return _serialize(opp)


def _serialize(opp: Opportunity) -> dict:
    return {
        "id": opp.id,
        "title": opp.title,
        "description": opp.description,
        "url": opp.url,
        "company_name": opp.company_name,
        "opportunity_type": opp.opportunity_type,
        "therapeutic_area": opp.therapeutic_area,
        "funding_amount": opp.funding_amount,
        "deadline": opp.deadline.isoformat() if opp.deadline else None,
        "date_discovered": opp.date_discovered.isoformat() if opp.date_discovered else None,
        "contact_info": opp.contact_info,
        "source_name": opp.source.name if opp.source else None,
        "crm_status": opp.crm_status or "new",
        "organization_id": opp.organization_id,
        "organization_name": opp.organization.name if opp.organization else None,
    }
