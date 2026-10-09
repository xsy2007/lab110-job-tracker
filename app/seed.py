from .db import SessionLocal
from .models import Source, User
from .security import hash_password

_DEFAULT_USERS = [
    ("user1", "user1", "user"),
    ("user2", "user2", "user"),
    ("maintainer", "maintainer", "maintainer"),
]

# One real big-company official site + two real public recruitment platforms.
_DEFAULT_SOURCES = [
    ("腾讯招聘", "company", "https://careers.tencent.com", "tencent"),
    ("实习僧", "platform", "https://www.shixiseng.com/interns", "shixiseng"),
    ("LinkedIn", "platform", "https://www.linkedin.com/jobs", "linkedin"),
]


def seed_defaults() -> None:
    db = SessionLocal()
    try:
        for username, password, role in _DEFAULT_USERS:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(username=username, password_hash=hash_password(password), role=role))
        for name, kind, base_url, collector in _DEFAULT_SOURCES:
            if not db.query(Source).filter(Source.name == name).first():
                db.add(Source(name=name, kind=kind, base_url=base_url, collector=collector))
        db.commit()
    finally:
        db.close()
