from fastapi import APIRouter, Depends, Request

from ..deps import get_current_maintainer
from ..models import User
from ..templating import templates

router = APIRouter()


@router.get("/maintenance")
def maintenance_page(request: Request, user: User = Depends(get_current_maintainer)):
    return templates.TemplateResponse(request, "maintenance.html", {"user": user})
