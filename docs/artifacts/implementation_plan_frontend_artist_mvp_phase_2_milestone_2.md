# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 2

Status: in progress on `2026-03-19`.

## Goal

Expose provider-native Yandex artist sections from `platform_catalog_lists` so the artist page can show direct albums and adjacent Yandex artist groupings separately from canonical linked releases.

## Scope

- extend `ArtistDetailResponse` with Yandex-native catalog sections
- load those sections from existing `platform_catalog_lists` rows for the linked Yandex artist
- render the new sections on `/ui/artists/{id}` without changing storage or ingestion behavior

## Acceptance

- `/artists/{id}` includes explicit Yandex catalog sections derived from stored provider data
- `/ui/artists/{id}` shows at least direct Yandex albums and similar artists in separate blocks
- canonical linked releases and provider-native Yandex lists remain visually distinct

## Non-Goals

- no schema migration
- no change to Yandex ingestion logic
- no change to missing-on-Yandex comparison logic
