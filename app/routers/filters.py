from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import SavedFilter, User
from ..templating import templates

router = APIRouter()


@router.get("/filters")
def filters_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    filters = (
        db.query(SavedFilter)
        .filter(SavedFilter.user_id == user.id)
        .order_by(SavedFilter.id.desc())
        .all()
    )
    return templates.TemplateResponse(request, "filters.html", {"user": user, "filters": filters})


@router.post("/filters/create")
def create_filter(
    request: Request,
    name: str = Form(...),
    keywords: str = Form(""),
    city: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db.add(SavedFilter(user_id=user.id, name=name.strip(), keywords=keywords.strip(), city=city.strip()))
    db.commit()
    return RedirectResponse("/filters", status_code=303)


@router.post("/filters/{fid}/update")
def update_filter(
    fid: int,
    name: str = Form(...),
    keywords: str = Form(""),
    city: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    f = db.query(SavedFilter).filter(SavedFilter.id == fid, SavedFilter.user_id == user.id).first()
    if f:
        f.name = name.strip()
        f.keywords = keywords.strip()
        f.city = city.strip()
        db.commit()
    return RedirectResponse("/filters", status_code=303)


@router.post("/filters/{fid}/delete")
def delete_filter(fid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.query(SavedFilter).filter(SavedFilter.id == fid, SavedFilter.user_id == user.id).first()
    if f:
        db.delete(f)
        db.commit()
    return RedirectResponse("/filters", status_code=303)


@router.get("/filters/{fid}/apply")
def apply_filter(fid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.query(SavedFilter).filter(SavedFilter.id == fid, SavedFilter.user_id == user.id).first()
    if f is None:
        return RedirectResponse("/filters", status_code=303)
    # Re-search the CURRENT jobs table with the saved conditions (never a snapshot).
    params = urlencode({"q": f.keywords, "city": f.city})
    return RedirectResponse(f"/jobs?{params}", status_code=303)
