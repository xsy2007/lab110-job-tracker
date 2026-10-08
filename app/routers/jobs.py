from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Job, User
from ..templating import templates

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    request: Request,
    q: str = "",
    city: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Job)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Job.title.like(like)) | (Job.company.like(like)) | (Job.description.like(like))
        )
    if city:
        query = query.filter(Job.city.like(f"%{city}%"))
    jobs = query.order_by(Job.first_seen_at.desc()).all()
    return templates.TemplateResponse(
        request, "jobs.html", {"user": user, "jobs": jobs, "q": q, "city": city}
    )


@router.get("/jobs/{job_id}")
def job_detail(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    return templates.TemplateResponse(request, "job_detail.html", {"user": user, "job": job})
