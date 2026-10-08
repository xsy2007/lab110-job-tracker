from .db import SessionLocal
from .models import Source, User
from .security import hash_password

_DEFAULT_USERS = [
    ("user1", "user1", "user"),
    ("user2", "user2", "user"),
    ("maintainer", "maintainer", "maintainer"),
]

# Two real sources: a real recruitment platform and a real big-company official site.
_DEFAULT_SOURCES = [
    ("拉勾网", "platform", "https://www.lagou.com", "lagou"),
    ("字节跳动招聘", "company", "https://jobs.bytedance.com", "bytedance"),
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
