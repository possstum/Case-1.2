# Implementation Plan: Branch Push And GitHub PR

Status: completed on `2026-03-23`.

## Summary

- Goal: safely package the current `yandex-catalog-ingest-pr` worktree into one Git commit, push the branch to `origin`, and open a GitHub PR.
- Constraint: do not widen product scope or edit unrelated subsystems; this slice is limited to git/github delivery plus required documentation artifacts.
- Source of truth:
  - `docs/project_brief.md`
  - current local worktree via `git status --short --branch`
  - `yeet` skill workflow

## Grounded Facts

- Current branch: `yandex-catalog-ingest-pr`
- The branch already tracks `origin/yandex-catalog-ingest-pr`.
- The worktree contains tracked and untracked local changes, so delivery requires:
  - review of changed files
  - a compact commit message that matches the actual diff
  - a PR title/body grounded in the current branch contents
- GitHub delivery depends on:
  - installed `gh`
  - authenticated `gh auth status`
  - successful `git push -u origin $(git branch --show-current)`

## Scope

In scope:

- inspect current diff and changed-file inventory
- verify local `gh` availability and auth status
- commit the current worktree once with a terse message
- push the existing branch
- create a draft PR with a real markdown body
- record the milestone in a walkthrough artifact

Out of scope:

- new application features
- schema or runtime changes unrelated to the existing worktree
- rewriting historical commits
- touching more than the git/github delivery subsystem in this milestone

## Milestones

### Milestone 0: Planning Artifact

Subsystem:

- planning artifacts

Files:

- `docs/artifacts/implementation_plan_branch_push_pr.md`

Edits:

- create the plan artifact first before git mutations
- keep the plan focused on the current delivery task only

Validation:

- `sed -n '1,220p' docs/artifacts/implementation_plan_branch_push_pr.md`

Tests:

- none

### Milestone 1: Branch Delivery And PR

Subsystem:

- git/github delivery

Files:

- current changed worktree files as discovered by `git status --short`
- `docs/artifacts/walkthrough_branch_push_pr.md`

Edits:

- inspect the diff and derive a concise commit description from real changes
- verify `gh --version` and `gh auth status`
- stage all current changes with `git add -A`
- create one commit
- push the current branch with tracking
- create a draft PR with a detailed markdown body saved through a temp file or repo artifact
- record changed files, commands, and checks in the walkthrough artifact

Validation:

- `git status --short --branch`
- `git diff --stat`
- `gh --version`
- `gh auth status`
- `git push -u origin $(git branch --show-current)`
- `gh pr create --draft --fill --head $(git branch --show-current)`

Tests:

- at minimum, report the tests already executed for the current worktree or explicitly record that no new tests were run in this delivery-only milestone

## Exit Criteria

- local branch is committed
- remote branch is updated
- draft PR exists on GitHub
- walkthrough artifact records changed files, commands, and test status for the milestone

## Outcome

- local commit created: `9e3a8d4 Add release hardening stage 1 demo readiness`
- branch pushed to `origin/yandex-catalog-ingest-pr`
- draft PR created: `https://github.com/possstum/Case-1.2/pull/1`
