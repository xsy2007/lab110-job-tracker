import os

from app.collectors.base import JobItem
from app.collectors.shixiseng import _clean, _job_from_dict, _salary
from app.models import Follow, Job, Source, User, UserActivity
from app.services.collection import apply_items, create_run, run_collection
from app.services.playback import run_playback


def _source(db, collector="playback"):
    return db.query(Source).filter(Source.collector == collector).first()


def _user(db, username="user1"):
    return db.query(User).filter(User.username == username).first()


def _p001(requirements):
    return JobItem(
        source_job_id="P001", title="后端工程师", company="甲公司", city="北京",
        source_url="https://example.com/jobs/P001", description="后端",
        requirements=requirements, salary="20-30k",
    )


# 1. unauthenticated access to a protected HTML page -> redirect /login
def test_unauthenticated_redirect(client):
    r = client.get("/jobs", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


# 2a. normal user cannot access /maintenance
def test_user_cannot_access_maintenance(client):
    client.post("/login", data={"username": "user1", "password": "x"}, follow_redirects=False)
    r = client.get("/maintenance")
    assert r.status_code == 403


# 2b. maintainer can access /maintenance
def test_maintainer_can_access_maintenance(client):
    client.post("/login", data={"username": "maintainer", "password": "x"}, follow_redirects=False)
    r = client.get("/maintenance")
    assert r.status_code == 200


# 3. re-follow: changes while unfollowed produce no activity; after re-follow only new changes do
def test_refollow_semantics(db):
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
    run = create_run(db, src.id)
    apply_items(db, run, [_p001("熟悉 Docker")])  # change while unfollowed
    db.commit()
    assert db.query(UserActivity).filter(UserActivity.user_id == u.id).count() == 1

    db.add(Follow(user_id=u.id, job_id=p001.id))
    db.commit()
    run = create_run(db, src.id)
    apply_items(db, run, [_p001("熟悉 K8s")])  # change after re-follow
    db.commit()
    assert db.query(UserActivity).filter(UserActivity.user_id == u.id).count() == 2


# 4. tests must not pollute the real evidence/ directory
def test_evidence_isolation(db, session_factory):
    from app.config import EVIDENCE_DIR

    before = set(os.listdir(EVIDENCE_DIR))
    broken = _source(db, "broken")
    run_collection(broken.id, session_factory=session_factory)  # would write meta if not isolated
    after = set(os.listdir(EVIDENCE_DIR))
    assert before == after


# 5. shixiseng parser basics
def test_shixiseng_clean():
    assert _clean("&#xe78a&&#xee73 餐饮部实习&#xf12c") == "餐饮部实习"
    assert _clean("新媒体运营实习（短视频/小红书）") == "新媒体运营实习（短视频/小红书）"


def test_shixiseng_job_from_dict():
    j = _job_from_dict(
        {
            "uuid": "inn_test1", "name": "&#xe78a后端实习", "cname": "甲公司",
            "city": "上海", "industry": "互联网", "degree": "本科",
            "minsalary": 150, "maxsalary": 200,
        }
    )
    assert j.source_job_id == "inn_test1"
    assert j.title == "后端实习"
    assert j.company == "甲公司"
    assert j.city == "上海"
    assert j.source_url == "https://www.shixiseng.com/intern/detail?uuid=inn_test1"
    assert j.salary == "150-200元/天"
    assert j.requirements == "本科"


def test_shixiseng_salary():
    assert _salary({"minsalary": 150, "maxsalary": 200}) == "150-200元/天"
    assert _salary({"minsalary": None, "maxsalary": 200}) == ""


def test_evidence_names_unique(db):
    from app.services.collection import _evidence_path, create_run

    src = _source(db)
    run = create_run(db, src.id)
    a = _evidence_path(src, run, "json")
    b = _evidence_path(src, run, "json")  # even the same run → distinct token
    assert a.name != b.name
    assert a.suffix == ".json"
    assert a.stem.split("_")[1] == "run"
    assert a.stem.split("_")[2] == str(run.id)
    assert _evidence_path(src, run, "meta.json").name.endswith(".meta.json")
