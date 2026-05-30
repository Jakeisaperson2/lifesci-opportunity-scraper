from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database.session import get_db
from database.models import Task

router = APIRouter(prefix="/crm/tasks", tags=["crm"])


class TaskIn(BaseModel):
    task_name: str
    due_date: Optional[datetime] = None
    priority: Optional[str] = "medium"
    assigned_to: Optional[str] = None
    opportunity_id: Optional[int] = None
    status: Optional[str] = "open"


def _ser(t: Task) -> dict:
    return {
        "id": t.id,
        "task_name": t.task_name,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "priority": t.priority,
        "assigned_to": t.assigned_to,
        "opportunity_id": t.opportunity_id,
        "opportunity_title": t.opportunity.title if t.opportunity else None,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("")
def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    opportunity_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Task)
    if status:
        q = q.filter(Task.status == status)
    if priority:
        q = q.filter(Task.priority == priority)
    if opportunity_id:
        q = q.filter(Task.opportunity_id == opportunity_id)
    total = q.count()
    items = q.order_by(Task.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "items": [_ser(t) for t in items],
    }


@router.post("")
def create_task(body: TaskIn, db: Session = Depends(get_db)):
    t = Task(**body.dict())
    db.add(t)
    db.commit()
    db.refresh(t)
    return _ser(t)


@router.get("/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return _ser(t)


@router.put("/{task_id}")
def update_task(task_id: int, body: TaskIn, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return _ser(t)


@router.patch("/{task_id}/status")
def patch_task_status(task_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    t.status = status
    db.commit()
    return _ser(t)


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(t)
    db.commit()
    return {"deleted": True}
