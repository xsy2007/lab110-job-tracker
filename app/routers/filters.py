from fastapi import APIRouter, Depends, Request

from ..deps import get_current_user
from ..models import User
from ..templating import templates

router = APIRouter()


@router.get("/filters")
def filters_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "filters.html", {"user": user})
