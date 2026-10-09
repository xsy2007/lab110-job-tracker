import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User, UserActivity
from ..templating import templates

router = APIRouter()


@router.get("/activity")
def activity_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    activities = (
        db.query(UserActivity)
        .filter(UserActivity.user_id == user.id)
        .order_by(UserActivity.created_at.desc())
        .all()
    )
    items = []
    for a in activities:
        try:
            payload = json.loads(a.payload or "{}")
        except Exception:
            payload = {}
        changes = [(k, v.get("before"), v.get("after")) for k, v in payload.items()]
        items.append({"activity": a, "changes": changes})
    return templates.TemplateResponse(request, "activity.html", {"user": user, "items": items})
