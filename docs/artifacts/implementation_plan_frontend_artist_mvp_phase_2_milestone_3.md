# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 3

Status: in progress on `2026-03-19`.

## Goal

Replace the current `Missing on Yandex` derivation from linked canonical releases with a dedicated artist-level comparison read model.

## Scope

- add a dedicated artist comparison payload for missing-on-Yandex browsing
- compare canonical artist releases against stored Yandex artist catalog evidence
- render the artist page from the new read model instead of filtering `detail.releases`

## Acceptance

- `/artists/{id}` returns a dedicated `missing_on_yandex_view`
- the read model uses provider-native Yandex catalog data when available
- `/ui/artists/{id}` explains which releases are still unresolved versus which have Yandex-native candidates but no canonical link yet

## Non-Goals

- no schema migration
- no provider-side live verification
- no change to ingestion persistence rules
