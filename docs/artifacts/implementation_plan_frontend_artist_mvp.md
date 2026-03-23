# Implementation Plan: Frontend Artist MVP

Status: approved on `2026-03-19`.

## Summary

- Goal: make the frontend MVP usable for artist lookup.
- User flow: enter an artist query on `/ui`, open the canonical artist page, and get readable release/album information with explicit platform presence and a separate section for releases missing from Yandex.
- Source of truth: current runtime and `docs/project_brief.md`.

## Milestones

### Milestone 1: Artist Read Model

Subsystem: API schemas and artist service

- extend the artist detail read model with release-level platform availability
- expose whether each related release is missing on Yandex
- keep the model conservative and derived from canonical release links

Acceptance:

- `/artists/{id}` returns release records with enough data to render platform presence and a missing-on-Yandex section

### Milestone 2: Frontend Artist Page

Subsystem: web rendering

- redesign the artist detail page around release cards instead of a plain list
- add a dedicated `Missing on Yandex` section
- keep the existing site visual language and mobile behavior

Acceptance:

- `/ui/artists/{id}` is readable and clearly shows albums/releases and Yandex gaps

### Milestone 3: Verification And Remaining MVP Gap List

Subsystem: tests and artifacts

- add regression coverage for API and web rendering
- run the local checks
- document the remaining work to reach the requested frontend MVP

Acceptance:

- tests pass
- follow-up steps are explicit and scoped
