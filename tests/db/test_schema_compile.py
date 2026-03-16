from __future__ import annotations

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db import models  # noqa: F401
from app.db.base import Base


def test_schema_compiles_for_sqlite_and_postgresql() -> None:
    dialects = [sqlite.dialect(), postgresql.dialect()]

    assert Base.metadata.tables

    for dialect in dialects:
        for table in Base.metadata.sorted_tables:
            compiled_table = str(CreateTable(table).compile(dialect=dialect))
            assert table.name in compiled_table

            for index in table.indexes:
                compiled_index = str(CreateIndex(index).compile(dialect=dialect))
                assert index.name in compiled_index
