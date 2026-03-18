# Walkthrough: Frontend Artist MVP Milestone 1

Status: completed on `2026-03-19`.

## Goal

Extend the artist read model so the frontend can show release-level platform presence and a dedicated missing-on-Yandex section.

## Changed Files

- `app/api/schemas/entities.py`
- `app/services/artist_service.py`

## Commands Run

```bash
.venv/bin/python -m pytest -q tests/api/test_entities.py
```

## Tests Run

- `.venv/bin/python -m pytest -q tests/api/test_entities.py` -> `4 passed in 0.44s`

## Result

Artist detail payloads now include release-level platform availability, missing-platforms, track counts, and an explicit `is_missing_yandex` flag derived from canonical release links.
