from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import get_db
from .models import User


class NotAuthenticatedError(Exception):
    """Raised when a protected route is hit without a valid session."""


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise NotAuthenticatedError()
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        raise NotAuthenticatedError()
    return user


def get_current_maintainer(user: User = Depends(get_current_user)) -> User:
    if user.role != "maintainer":
        raise HTTPException(status_code=403, detail="Maintainer only")
    return user
