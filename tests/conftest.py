import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
import app.models  # noqa: F401  register all models
from app.models import Source, User
from app.security import hash_password


@pytest.fixture
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    yield Session
    engine.dispose()


@pytest.fixture
def db(session_factory):
    s = session_factory()
    s.add_all(
        [
            User(username="user1", password_hash=hash_password("x"), role="user"),
            User(username="user2", password_hash=hash_password("x"), role="user"),
            User(username="maintainer", password_hash=hash_password("x"), role="maintainer"),
            Source(name="playback", kind="platform", base_url="https://example.com", collector="playback"),
            Source(name="broken", kind="company", base_url="https://example.com", collector="broken"),
        ]
    )
    s.commit()
    yield s
    s.close()
