from app.collectors.base import JobItem
from app.models import (
    Follow,
    Job,
    JobChange,
    JobVersion,
    SavedFilter,
    Source,
    User,
    UserActivity,
)
from app.services.collection import apply_items, create_run, run_collection
from app.services.playback import run_playback


def _source(db, collector="playback"):
    return db.query(Source).filter(Source.collector == collector).first()


def _user(db, username="user1"):
    return db.query(User).filter(User.username == username).first()


# 1. duplicate refresh -> no duplicate change
def test_duplicate_refresh_no_duplicate_change(db):
    src = _source(db)
    run_playback(db, src.id, "baseline.json")
    assert db.query(JobChange).count() == 0
    run_playback(db, src.id, "requirements_changed.json")
    n1 = db.query(JobChange).count()
    assert n1 == 1
    run_playback(db, src.id, "requirements_changed.json")
    assert db.query(JobChange).count() == n1  # no new change


# 2. same title + different source_job_id -> two jobs
def test_same_title_different_source_job_id(db):
    src = _source(db)
    run = create_run(db, src.id)
    apply_items(
        db,
        run,
        [
            JobItem(source_job_id="A1", title="工程师", company="X", city="北京", source_url="https://x/1"),
            JobItem(source_job_id="A2", title="工程师", company="Y", city="上海", source_url="https://x/2"),
        ],
    )
    db.commit()
    jobs = db.query(Job).filter(Job.title == "工程师").all()
    assert len(jobs) == 2
    assert {j.source_job_id for j in jobs} == {"A1", "A2"}


# 3. change before follow -> no activity
def test_change_before_follow_no_activity(db):
    src = _source(db)
    u = _user(db)
    run_playback(db, src.id, "baseline.json")
    run_playback(db, src.id, "requirements_changed.json")  # change happens first
    p001 = db.query(Job).filter(Job.source_job_id == "P001").first()
    db.add(Follow(user_id=u.id, job_id=p001.id))
    db.commit()
    assert db.query(UserActivity).filter(UserActivity.user_id == u.id).count() == 0


# 4. unfollow -> no new activity, old activity retained
def test_unfollow_no_new_activity(db):
    src = _source(db)
    u = _user(db)
    run_playback(db, src.id, "baseline.json")
    p001 = db.query(Job).filter(Job.source_job_id == "P001").first()
    f = Follow(user_id=u.id, job_id=p001.id)
    db.add(f)
    db.commit()
    run_playback(db, src.id, "requirements_changed.json")  # change while following
    assert db.query(UserActivity).filter(UserActivity.user_id == u.id).count() == 1
    db.delete(f)
    db.commit()
    run_playback(db, src.id, "explicit_closed.json")  # closes P002, not followed
    assert db.query(UserActivity).filter(UserActivity.user_id == u.id).count() == 1


# 5. source failure -> old jobs remain open, run FAILED
def test_source_failure_keeps_old_jobs(db, session_factory):
    src = _source(db)
    run_playback(db, src.id, "baseline.json")
    assert db.query(Job).filter(Job.source_id == src.id).count() == 3
    broken = _source(db, "broken")
    run = run_collection(broken.id, session_factory=session_factory)
    assert run.status == "FAILED"
    assert run.error_message
    jobs = db.query(Job).filter(Job.source_id == src.id).all()
    assert len(jobs) == 3
    assert all(j.status == "OPEN" for j in jobs)


# 6. user1/user2 isolation
def test_user_isolation(db):
    u1 = _user(db, "user1")
    u2 = _user(db, "user2")
    db.add(SavedFilter(user_id=u1.id, name="f1", keywords="python", city="北京"))
    db.commit()
    assert db.query(SavedFilter).filter(SavedFilter.user_id == u2.id).count() == 0
    assert db.query(SavedFilter).filter(SavedFilter.user_id == u1.id).count() == 1

    src = _source(db)
    run_playback(db, src.id, "baseline.json")
    p001 = db.query(Job).filter(Job.source_job_id == "P001").first()
    db.add(Follow(user_id=u1.id, job_id=p001.id))
    db.commit()
    run_playback(db, src.id, "requirements_changed.json")
    assert db.query(UserActivity).filter(UserActivity.user_id == u1.id).count() == 1
    assert db.query(UserActivity).filter(UserActivity.user_id == u2.id).count() == 0


# 7. saved filter reuses current data instead of result snapshot
def test_filter_reuses_current_data(db):
    src = _source(db)
    u = _user(db)
    run_playback(db, src.id, "baseline.json")
    db.add(SavedFilter(user_id=u.id, name="f", keywords="工程师", city=""))
    db.commit()
    f = db.query(SavedFilter).first()

    def apply(filt):
        like = f"%{filt.keywords}%"
        return db.query(Job).filter(Job.title.like(like)).all()

    assert len(apply(f)) == 3
    run = create_run(db, src.id)
    apply_items(
        db, run, [JobItem(source_job_id="P004", title="算法工程师", company="丁", city="杭州", source_url="https://x/P004")]
    )
    db.commit()
    assert len(apply(f)) == 4  # re-searched current data, not a snapshot


# 8. first collection creates baseline but zero job_change
def test_first_collection_baseline_zero_change(db):
    src = _source(db)
    run = run_playback(db, src.id, "baseline.json")
    assert run.is_baseline is True
    assert db.query(Job).count() == 3
    assert db.query(JobVersion).count() == 3
    assert db.query(JobChange).count() == 0


# 9. playback four scenarios
def test_playback_four_scenarios(db):
    src = _source(db)
    run_playback(db, src.id, "baseline.json")
    assert db.query(JobChange).count() == 0

    # requirements_changed -> clear before/after
    run_playback(db, src.id, "requirements_changed.json")
    ch = db.query(JobChange).filter(JobChange.field == "requirements").all()
    assert len(ch) == 1
    assert ch[0].before_value == "熟悉 Python"
    assert ch[0].after_value == "熟悉 FastAPI 和 SQLAlchemy"

    # explicit_closed -> only P002 closed
    run_playback(db, src.id, "explicit_closed.json")
    assert db.query(Job).filter(Job.source_job_id == "P002").first().status == "CLOSED"
    assert db.query(Job).filter(Job.source_job_id == "P001").first().status == "OPEN"

    # source_timeout -> FAILED, no job closed
    run = run_playback(db, src.id, "source_timeout.json")
    assert run.status == "FAILED"
    assert run.error_message == "timeout"
    assert db.query(Job).filter(Job.source_job_id == "P001").first().status == "OPEN"
    assert db.query(Job).filter(Job.source_job_id == "P003").first().status == "OPEN"
