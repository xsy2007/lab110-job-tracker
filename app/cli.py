import sys

from .db import SessionLocal, init_db
from .models import Source
from .seed import seed_defaults
from .services.collection import run_collection


def main(argv=None):
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    init_db()
    seed_defaults()
    db = SessionLocal()
    try:
        sources = db.query(Source).order_by(Source.id).all()
        if argv:
            sources = [s for s in sources if s.name in argv or s.collector in argv]
        for s in sources:
            print(f"== collect {s.name} ({s.collector}) ==")
            run = run_collection(s.id)
            print(
                f"   run_id={run.id} status={run.status} baseline={run.is_baseline} "
                f"created={run.created_count} updated={run.updated_count} "
                f"unchanged={run.unchanged_count} failed={run.failed_count}"
            )
            if run.error_message:
                print(f"   error={run.error_message}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
