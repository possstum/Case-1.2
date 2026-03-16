# НЕТвРФ

Ты работаешь в проекте НЕТвРФ.

Главные правила:
1. Сначала создавай `Implementation Plan` artifact. Не пиши код, пока план не проверен.
2. Любую большую задачу дели на маленькие milestone-ы.
3. После каждого milestone:
   - покажи список измененных файлов
   - покажи команды запуска
   - покажи какие тесты запускал
   - создай `Walkthrough` artifact
4. Стек проекта фиксирован:
   - FastAPI
   - Pydantic
   - SQLAlchemy 2.x
   - Alembic
   - Redis + RQ
5. Dev DB = SQLite WAL.
6. Staging/Prod = PostgreSQL.
7. Никогда не хардкодь токены, cookies, headers.
8. Никогда не логируй Authorization, Cookie, Token.
9. Для matching prefer ambiguous over false match.
10. Любая реализация должна опираться на `docs/project_brief.md`.
11. Не меняй более одной подсистемы за один milestone.
12. Любой diff должен быть компактным и объяснимым.
