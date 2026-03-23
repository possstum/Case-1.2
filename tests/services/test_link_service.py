from __future__ import annotations

from sqlalchemy import event, func, select

from app.db.models import PlatformArtist
from app.db.session import get_session_factory
from app.services.link_service import LinkService
from app.providers import ProviderName
from tests.test_support import make_artist


def test_link_service_recovers_when_platform_artist_is_inserted_concurrently(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    session_factory = get_session_factory()
    session = session_factory()
    competing_session = session_factory()
    entity = make_artist(ProviderName.YANDEX, "1014281", "Motorama")
    injected = False

    def insert_competing_row(target_session, flush_context, instances) -> None:
        nonlocal injected
        if target_session is not session or injected:
            return
        injected = True
        competing_session.add(
            PlatformArtist(
                platform=entity.provider.value,
                platform_id=entity.provider_id,
                display_name="Motorama stale",
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                raw_json={"source": "competing-session"},
            )
        )
        competing_session.commit()

    event.listen(session, "before_flush", insert_competing_row)
    try:
        row = LinkService(session).persist_platform_entity(entity)
        session.commit()
    finally:
        event.remove(session, "before_flush", insert_competing_row)
        competing_session.close()
        session.close()

    verification_session = session_factory()
    try:
        stored_rows = verification_session.scalars(select(PlatformArtist)).all()
        assert len(stored_rows) == 1
        assert stored_rows[0].id == row.id
        assert stored_rows[0].display_name == "Motorama"
        assert stored_rows[0].raw_json == {}
        assert verification_session.scalar(select(func.count()).select_from(PlatformArtist)) == 1
    finally:
        verification_session.close()
