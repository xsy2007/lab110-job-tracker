from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_maintainer
from ..models import CollectionRun, Source, User
from ..services.collection import run_collection
from ..templating import templates

router = APIRouter()


@router.get("/maintenance")
def maintenance_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_maintainer),
):
    sources = db.query(Source).order_by(Source.id).all()
    runs = db.query(CollectionRun).order_by(CollectionRun.id.desc()).limit(20).all()
    source_names = {s.id: s.name for s in sources}
    return templates.TemplateResponse(
        request,
        "maintenance.html",
        {"user": user, "sources": sources, "runs": runs, "source_names": source_names},
    )


@router.post("/maintenance/collect/{source_id}")
def collect_source(
    source_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_maintainer),
):
    run_collection(source_id)
    return RedirectResponse("/maintenance", status_code=303)


@router.post("/maintenance/collect-all")
def collect_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_maintainer),
):
    # Per-source isolation: one source failing must not block the others.
    for s in db.query(Source).order_by(Source.id).all():
        try:
            run_collection(s.id)
        except Exception:
            continue
    return RedirectResponse("/maintenance", status_code=303)
