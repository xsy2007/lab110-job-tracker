from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # project root
DATA_DIR = BASE_DIR / "data"
EVIDENCE_DIR = BASE_DIR / "evidence"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"

for _d in (DATA_DIR, EVIDENCE_DIR, SNAPSHOTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'lab110.db'}"

# Dev-only session signing key; override in production.
SECRET_KEY = "lab110-dev-secret-key-change-me"
