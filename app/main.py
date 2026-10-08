from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import SECRET_KEY
from .db import init_db
from .deps import NotAuthenticatedError
from .routers import activity, auth, filters, follows, jobs, maintenance
from .seed import seed_defaults


def create_app() -> FastAPI:
    app = FastAPI(title="Lab110 Job Tracker")
    app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=7 * 24 * 3600)

    init_db()
    seed_defaults()

    app.include_router(auth.router)
    app.include_router(jobs.router)
    app.include_router(filters.router)
    app.include_router(follows.router)
    app.include_router(activity.router)
    app.include_router(maintenance.router)

    @app.exception_handler(NotAuthenticatedError)
    async def _not_auth(request, exc):
        return RedirectResponse("/login", status_code=303)

    @app.get("/")
    def root():
        return RedirectResponse("/jobs", status_code=303)

    return app


app = create_app()
