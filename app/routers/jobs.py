from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..deps import get_current_user
from ..models import Follow, Job, User
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
    query = db.query(Job).options(joinedload(Job.source))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Job.title.like(like)) | (Job.company.like(like)) | (Job.description.like(like))
        )
    if city:
        query = query.filter(Job.city.like(f"%{city}%"))
    jobs = query.order_by(Job.first_seen_at.desc()).all()
    followed = {f.job_id for f in db.query(Follow).filter(Follow.user_id == user.id).all()}
    return templates.TemplateResponse(
        request, "jobs.html", {"user": user, "jobs": jobs, "q": q, "city": city, "followed": followed}
    )


@router.get("/jobs/{job_id}")
def job_detail(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    followed = (
        db.query(Follow).filter(Follow.user_id == user.id, Follow.job_id == job_id).first()
        is not None
    )
    return templates.TemplateResponse(
        request, "job_detail.html", {"user": user, "job": job, "followed": followed}
    )


@router.post("/jobs/{job_id}/follow")
def follow_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not db.query(Follow).filter(Follow.user_id == user.id, Follow.job_id == job_id).first():
        db.add(Follow(user_id=user.id, job_id=job_id))
        db.commit()
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@router.post("/jobs/{job_id}/unfollow")
def unfollow_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.query(Follow).filter(Follow.user_id == user.id, Follow.job_id == job_id).first()
    if f:
        db.delete(f)
        db.commit()
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)
