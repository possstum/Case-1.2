# Implementation Plan: Production-Like Verification

Status: planned on `2026-03-19`.

## Summary

- Goal: run a live staging verification with real provider tokens after the current merge-ready PR is opened or merged.
- Scope: runtime verification only.
- Out of scope: no code changes, no docs claims before this milestone is green.

## Required Environment

- staging-like PostgreSQL
- staging-like Redis
- real `YOUTUBE_MUSIC_TOKEN`
- real `YANDEX_MUSIC_TOKEN`
- API process started from the staged branch
- worker process started against the same Redis queue

## Verification Matrix

- `GET /search`
  - use a known live query
  - confirm the response returns a real result set and does not degrade into provider-disabled behavior
- `GET /ui`
  - confirm the landing page renders normally
  - confirm a searched `/ui` page renders normal HTML for the same live query
- `POST /sync/{kind}/{target_id}`
  - create a real sync job using a canonical ID obtained from the live search response
- `GET /jobs/{job_id}`
  - confirm the job transitions through queued/running/terminal states
- worker execution
  - confirm the worker consumes the queued job
  - require at least one Yandex refresh success-path in the final payload

## Acceptance Rules

- the milestone is green only if `/search`, `/ui`, sync enqueue, job polling, and worker execution all work in the same live environment
- YouTube-side failure is acceptable only if it is explicitly attributable to the current `YouTubeMusicClient.get_*()` stubs and is reflected in the job payload
- only after this milestone is green may docs be updated with any production-like readiness claims
