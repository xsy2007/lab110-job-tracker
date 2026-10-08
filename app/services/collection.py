import json
from datetime import datetime, timezone

from ..collectors import get_collector
from ..config import EVIDENCE_DIR
from ..db import SessionLocal
from ..models import CollectionRun, Follow, Job, JobChange, JobVersion, Source, UserActivity


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


# Content fields whose change produces a JobChange (before/after).
_COMPARED_FIELDS = ("title", "description", "requirements", "salary", "status", "deadline")


def create_run(db, source_id: int) -> CollectionRun:
    """Create a run, marking it baseline when the source has no prior success."""
    has_prior_success = (
        db.query(CollectionRun)
        .filter(CollectionRun.source_id == source_id, CollectionRun.status == "SUCCESS")
        .first()
        is not None
    )
    run = CollectionRun(source_id=source_id, status="RUNNING", is_baseline=not has_prior_success)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def apply_items(db, run: CollectionRun, items) -> tuple[int, int, int, int]:
    """Core upsert + change detection + activity generation.

    - First run (baseline) only creates jobs + versions, never job_changes.
    - Identical content produces no new job_change.
    - Jobs not present in `items` are left untouched (never auto-CLOSED).
    - Activities are generated only for users following a job at this moment.
    """
    source_id = run.source_id
    created = updated = unchanged = failed = 0
    changed_jobs = []  # (job_id, activity_type, payload_dict)

    for item in items:
        try:
            existing = (
                db.query(Job)
                .filter(Job.source_id == source_id, Job.source_job_id == item.source_job_id)
                .first()
            )
            if existing is None:
                job = Job(
                    source_id=source_id,
                    source_job_id=item.source_job_id,
                    title=item.title,
                    company=item.company,
                    city=item.city,
                    source_url=item.source_url,
                    description=item.description,
                    requirements=item.requirements,
                    salary=item.salary,
                    status=item.status,
                    deadline=item.deadline,
                    last_seen_run_id=run.id,
                )
                db.add(job)
                db.flush()
                db.add(
                    JobVersion(
                        job_id=job.id, run_id=run.id, title=job.title,
                        description=job.description, requirements=job.requirements,
                        salary=job.salary, status=job.status, deadline=job.deadline,
                    )
                )
                created += 1
            else:
                new_values = {
                    "title": item.title,
                    "description": item.description,
                    "requirements": item.requirements,
                    "salary": item.salary,
                    "status": item.status,
                    "deadline": item.deadline,
                }
                changed = []
                for f in _COMPARED_FIELDS:
                    if _fmt(getattr(existing, f)) != _fmt(new_values[f]):
                        changed.append((f, getattr(existing, f), new_values[f]))

                if changed:
                    payload = {}
                    for f, old, new in changed:
                        db.add(
                            JobChange(
                                job_id=existing.id, run_id=run.id, field=f,
                                before_value=_fmt(old), after_value=_fmt(new),
                            )
                        )
                        setattr(existing, f, new)
                        payload[f] = {"before": _fmt(old), "after": _fmt(new)}
                    if existing.status == "CLOSED" and existing.closed_at is None:
                        existing.closed_at = _now()
                    existing.last_seen_at = _now()
                    existing.last_seen_run_id = run.id
                    db.add(
                        JobVersion(
                            job_id=existing.id, run_id=run.id, title=existing.title,
                            description=existing.description, requirements=existing.requirements,
                            salary=existing.salary, status=existing.status, deadline=existing.deadline,
                        )
                    )
                    updated += 1
                    atype = "closed" if existing.status == "CLOSED" else "changed"
                    changed_jobs.append((existing.id, atype, payload))
                else:
                    existing.last_seen_at = _now()
                    existing.last_seen_run_id = run.id
                    unchanged += 1
        except Exception:
            failed += 1

    # Activity generation: only users following the job right now get an entry.
    for job_id, atype, payload in changed_jobs:
        followers = db.query(Follow).filter(Follow.job_id == job_id).all()
        for f in followers:
            db.add(
                UserActivity(
                    user_id=f.user_id,
                    job_id=job_id,
                    activity_type=atype,
                    payload=json.dumps(payload, ensure_ascii=False),
                )
            )

    return created, updated, unchanged, failed


def run_collection(source_id: int, session_factory=SessionLocal) -> CollectionRun:
    """Collect one source over the network and persist jobs.

    A per-source failure never touches existing data and never affects other sources."""
    db = session_factory()
    try:
        source = db.get(Source, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        run = create_run(db, source_id)

        try:
            collector = get_collector(source.collector)
            result = collector.collect()
        except Exception as exc:  # source failure: keep old data, mark run failed
            run.status = "FAILED"
            run.error_message = f"{type(exc).__name__}: {exc}"
            run.finished_at = _now()
            db.commit()
            db.refresh(run)
            return run

        # Evidence: raw response body, byte-for-byte, unmodified.
        evidence_dir = EVIDENCE_DIR / source.collector
        evidence_dir.mkdir(parents=True, exist_ok=True)
        ext = "json" if source.collector == "tencent" else "html"
        (evidence_dir / f"run_{run.id}.{ext}").write_text(result.raw, encoding="utf-8")

        created, updated, unchanged, failed = apply_items(db, run, result.items)

        run.status = "SUCCESS"
        run.created_count = created
        run.updated_count = updated
        run.unchanged_count = unchanged
        run.failed_count = failed
        run.finished_at = _now()
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()
