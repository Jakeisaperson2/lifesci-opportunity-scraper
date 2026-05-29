from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.session import get_db
from database.models import FacultyMember
from services.faculty_runner import run_faculty_scrape, run_tableau_enrichment

router = APIRouter(prefix="/faculty", tags=["faculty"])


@router.get("")
def list_faculty(
    search: Optional[str] = Query(None, description="Search name, department, research interests, or lab assets"),
    department: Optional[str] = Query(None),
    has_lab_data: Optional[bool] = Query(None, description="Filter to records with lab assets or project ideas"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(FacultyMember).filter(FacultyMember.is_active == True)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                FacultyMember.name.ilike(like),
                FacultyMember.department.ilike(like),
                FacultyMember.research_interests.ilike(like),
                FacultyMember.lab_assets.ilike(like),
                FacultyMember.project_ideas.ilike(like),
            )
        )

    if department:
        query = query.filter(FacultyMember.department.ilike(f"%{department}%"))

    if has_lab_data is True:
        query = query.filter(
            or_(
                FacultyMember.lab_assets != None,
                FacultyMember.project_ideas != None,
            )
        ).filter(
            or_(
                FacultyMember.lab_assets != "",
                FacultyMember.project_ideas != "",
            )
        )

    total = query.count()
    items = (
        query.order_by(FacultyMember.name)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
        "items": [_serialize(f) for f in items],
    }


@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    """Return distinct department names for the filter dropdown."""
    rows = (
        db.query(FacultyMember.department)
        .filter(
            FacultyMember.is_active == True,
            FacultyMember.department != None,
            FacultyMember.department != "",
        )
        .distinct()
        .order_by(FacultyMember.department)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/{faculty_id}")
def get_faculty(faculty_id: int, db: Session = Depends(get_db)):
    member = db.query(FacultyMember).filter(FacultyMember.id == faculty_id).first()
    if not member:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Faculty member not found")
    return _serialize(member)


@router.post("/refresh")
def refresh_faculty(background_tasks: BackgroundTasks):
    """Trigger a full NIH Reporter scrape + Tableau enrichment."""
    background_tasks.add_task(_refresh_and_enrich)
    return {"status": "started"}


@router.post("/enrich")
def enrich_faculty(background_tasks: BackgroundTasks):
    """Trigger only the Tableau enrichment (faster, no NIH scrape)."""
    background_tasks.add_task(run_tableau_enrichment)
    return {"status": "started"}


def _refresh_and_enrich():
    run_faculty_scrape()
    run_tableau_enrichment()


def _serialize(f: FacultyMember) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "title": f.title,
        "department": f.department,
        "school": f.school,
        "research_interests": f.research_interests,
        "lab_assets": f.lab_assets or "",
        "project_ideas": f.project_ideas or "",
        "email": f.email,
        "phone": f.phone,
        "profile_url": f.profile_url,
        "date_discovered": f.date_discovered.isoformat() if f.date_discovered else None,
        "last_updated": f.last_updated.isoformat() if f.last_updated else None,
    }
