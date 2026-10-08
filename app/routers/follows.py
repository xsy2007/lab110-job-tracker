from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Follow, Job, User
from ..templating import templates

router = APIRouter()


@router.get("/follows")
def follows_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    follows = (
        db.query(Follow)
        .filter(Follow.user_id == user.id)
        .order_by(Follow.created_at.desc())
        .all()
    )
    jobs = [db.get(Job, f.job_id) for f in follows]
    jobs = [j for j in jobs if j is not None]
    return templates.TemplateResponse(request, "follows.html", {"user": user, "jobs": jobs})
