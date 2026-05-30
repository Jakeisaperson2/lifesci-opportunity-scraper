from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.session import get_db
from database.models import Contact

router = APIRouter(prefix="/crm/contacts", tags=["crm"])


class ContactIn(BaseModel):
    name: str
    title: Optional[str] = None
    organization_id: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None


def _ser(c: Contact) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "title": c.title,
        "organization_id": c.organization_id,
        "organization_name": c.organization.name if c.organization else None,
        "email": c.email,
        "phone": c.phone,
        "linkedin": c.linkedin,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("")
def list_contacts(
    search: Optional[str] = Query(None),
    organization_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Contact)
    if search:
        q = q.filter(or_(
            Contact.name.ilike(f"%{search}%"),
            Contact.email.ilike(f"%{search}%"),
        ))
    if organization_id:
        q = q.filter(Contact.organization_id == organization_id)
    total = q.count()
    items = q.order_by(Contact.name).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "items": [_ser(c) for c in items],
    }


@router.post("")
def create_contact(body: ContactIn, db: Session = Depends(get_db)):
    c = Contact(**body.dict())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _ser(c)


@router.get("/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    return _ser(c)


@router.put("/{contact_id}")
def update_contact(contact_id: int, body: ContactIn, db: Session = Depends(get_db)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _ser(c)


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(c)
    db.commit()
    return {"deleted": True}
