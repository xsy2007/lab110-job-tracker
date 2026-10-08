"""Deterministic playback of the collection pipeline against snapshot fixtures.

Playback is independent of real collection: it feeds a snapshot JSON into the
same change-detection code, so the acceptance logic can be verified without the
network and without touching real jobs.
"""

import json
from datetime import datetime, timezone

from ..collectors.base import JobItem
from ..config import SNAPSHOTS_DIR
from .collection import apply_items, create_run


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_items(data: list) -> list[JobItem]:
    items = []
    for d in data:
        deadline = d.get("deadline")
        if deadline:
            deadline = datetime.fromisoformat(deadline)
        items.append(
            JobItem(
                source_job_id=d["source_job_id"],
                title=d.get("title", ""),
                company=d.get("company", ""),
                city=d.get("city", ""),
                source_url=d.get("source_url", ""),
                description=d.get("description", ""),
                requirements=d.get("requirements", ""),
                salary=d.get("salary", ""),
                status=d.get("status", "OPEN"),
                deadline=deadline,
            )
        )
    return items


def load_snapshot(name: str) -> list[JobItem]:
    return _to_items(json.loads((SNAPSHOTS_DIR / name).read_text(encoding="utf-8")))


def run_playback(db, source_id: int, snapshot_name: str):
    """Run the pipeline against a snapshot (no network). Returns the run."""
    raw = json.loads((SNAPSHOTS_DIR / snapshot_name).read_text(encoding="utf-8"))

    # A snapshot with "__error__" simulates a source failure (e.g. timeout).
    if isinstance(raw, dict) and "__error__" in raw:
        run = create_run(db, source_id)
        run.status = "FAILED"
        run.error_message = raw["__error__"]
        run.finished_at = _now()
        db.commit()
        db.refresh(run)
        return run

    run = create_run(db, source_id)
    created, updated, unchanged, failed = apply_items(db, run, _to_items(raw))
    run.status = "SUCCESS"
    run.created_count = created
    run.updated_count = updated
    run.unchanged_count = unchanged
    run.failed_count = failed
    run.finished_at = _now()
    db.commit()
    db.refresh(run)
    return run
