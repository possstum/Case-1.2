from __future__ import annotations

import json
from collections.abc import Sequence

from app.db.session import get_session_factory
from app.demo.data import DEFAULT_DEMO_IDENTIFIERS, seed_demo_catalog


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    session = get_session_factory()()
    try:
        state = seed_demo_catalog(
            session,
            identifiers=DEFAULT_DEMO_IDENTIFIERS,
            include_yandex_catalog_sections=True,
            include_finished_job=True,
        )
    finally:
        session.close()

    print("Seeded deterministic demo data:")
    print(
        json.dumps(
            {
                "artist_id": state.artist_id,
                "release_id": state.release_id,
                "track_id": state.track_id,
                "job_id": state.job_id,
                "rq_job_id": state.rq_job_id,
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
