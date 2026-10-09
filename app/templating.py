from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _dt(value, fmt="%Y-%m-%d %H:%M"):
    if value is None:
        return "—"
    return value.strftime(fmt)


def _badge(status):
    return {
        "OPEN": "badge-open",
        "SUCCESS": "badge-success",
        "CLOSED": "badge-closed",
        "FAILED": "badge-failed",
        "RUNNING": "badge-running",
    }.get((status or "").upper(), "badge-default")


templates.env.filters["dt"] = _dt
templates.env.filters["badge"] = _badge
