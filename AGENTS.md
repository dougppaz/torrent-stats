# AGENTS.md

Instructions for coding agents working on **torrent-stats**.

## Environment & Tooling

- **asdf-vm**: Manages tool versions (`.tool-versions`). Ensure correct Python and Go runtimes via asdf.
- **Python / Poetry (`torrent_stats/` - API)**: FastAPI + CouchDB (Repository pattern) + Redis (12h hourly hit buckets synced to CouchDB `total_hits`/`last_hit_at`, task leases). Agnostic storage profiles (FTP first via `fsspec`, recording profile key & storage parameters, rendering download URLs via profile templates). Routes defined in `api/openapi.yaml`.
  - **Dependency rule**: Never specify explicit versions when adding packages (`poetry add <pkg>`). Install first, inspect the installed version from `poetry.lock`, then consult documentation targeted to that exact version.
- **Go (`worker/` - Worker)**: Standalone binary. Communicates exclusively via authenticated HTTP API endpoints (`X-Worker-Key`). Claims tasks via `POST /worker/tasks/claim` enforcing 12h failure cooldowns (new torrents) and 6h update cooldowns (tracker stats), with ACK/leases and automatic tracker pruning after 3 consecutive failures.

## Quality Gates & Verification

- **Lint & Type Check**: Run `poetry run ruff check torrent_stats/`, `poetry run ruff format --check torrent_stats/`, and `poetry run mypy torrent_stats/` on **every change**.
- **Unit Tests & Coverage**: Run `poetry run pytest` on every change. All code changes must maintain **at least 90% test coverage** (`--cov-fail-under=90`).
- **Pre-commit**: Configured via `.pre-commit-config.yaml`. Run `pre-commit install` during setup.

## Workflow & Changes

- **Flow for Features & Fixes**: For any new implementation or bug fix, follow this workflow:
  1. Confirm with the user at the start of a session whether to proceed with this workflow. Once confirmed, continue.
  2. Create a new branch starting from an updated `main`.
  3. Implement using specs and TLC skills (`tlc-spec-driven`, etc.) when applicable.
  4. Commit changes atomically with passing quality gates.
  5. Push the branch and open a Merge Request (Pull Request) using the GitHub CLI (`gh pr create`).


- **Specifications are binding**: Feature shape and acceptance criteria live in `.specs/features/core-resolution/plan.md` (Approved: `user: "yes"`). API contracts live in `api/openapi.yaml`.
- **Atomic implementation**: Build strictly slice by slice. Verify every check against the plan.
