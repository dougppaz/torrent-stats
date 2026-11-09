# Tracker Stats Task Optimization Tasks

**Status**: Approved
**Approved**: 2026-11-07 - user: "aprovo o plan"

## Test Coverage Matrix

| Code Layer | Required Test Type | Minimum Coverage |
| --- | --- | --- |
| Models & Repositories (`torrent_stats/db/models.py`, `repository.py`) | unit | 90% |
| API Routers (`torrent_stats/api/routers/torrents.py`, `worker.py`) | unit | 90% |

## Gate Check Commands

| Type | Command |
| --- | --- |
| Quick | `poetry run pytest tests/test_api_worker.py` |
| Full | `poetry run pytest` |
| Build | `poetry run ruff check torrent_stats/ tests/ && poetry run ruff format --check torrent_stats/ tests/ && poetry run mypy torrent_stats/ && poetry run pytest --cov-fail-under=90` |

## Execution Plan

### Phase 1: Models & Repositories
- **T1: Nullable TrackerStats & Denormalized TaskDocument** (`torrent_stats/db/models.py`, `torrent_stats/db/repository.py`, `tests/test_models.py`)
  - Depends on: none
  - Tests: unit
  - Gate: Build

### Phase 2: API & Worker Endpoints
- **T2: Cooldown Bypass & Enriched Task Payloads** (`torrent_stats/api/routers/torrents.py`, `torrent_stats/api/routers/worker.py`, `tests/test_api_worker.py`, `tests/test_api_torrents.py`)
  - Depends on: T1
  - Tests: unit
  - Gate: Build

**Build**: `poetry run ruff check torrent_stats/ tests/ && poetry run ruff format --check torrent_stats/ tests/ && poetry run mypy torrent_stats/ && poetry run pytest --cov-fail-under=90`

## Task Breakdown

### T1: Nullable TrackerStats & Denormalized TaskDocument

- **Scope**: Update `TrackerStat` to have nullable `seeds`, `peers`, and `updated_at` (defaulting to `None`), and update `TaskDocument` to include `tracker_updated_at`.
- **Where**: `torrent_stats/db/models.py`, `torrent_stats/db/repository.py`, `tests/test_models.py`
**Tests**: unit
**Gate**: Build
- **Done when**:
  1. `TrackerStat` initializes with `seeds=None`, `peers=None`, `updated_at=None`.
  2. `TaskDocument` includes `tracker_updated_at: str | None = None`.
  3. Unit tests pass.
- **Commit**: `feat(db): make TrackerStat fields nullable and denormalize tracker_updated_at in TaskDocument`

### T2: Cooldown Bypass & Enriched Task Payloads

- **Scope**: Update `GET /torrents/:hash` and `POST /worker/tasks/claim` to handle null tracker stats, evaluate cooldown directly via `tracker_updated_at` on `TaskDocument` (bypassing when null), and include `tracker_url` and `updated_at` in task payloads.
- **Where**: `torrent_stats/api/routers/torrents.py`, `torrent_stats/api/routers/worker.py`, `tests/test_api_worker.py`, `tests/test_api_torrents.py`
**Tests**: unit
**Gate**: Build
- **Done when**:
  1. `POST /worker/tasks/claim` processes tasks with `tracker_updated_at=None` immediately ignoring cooldown without querying metadata.
  2. Response payloads for `/torrents/:hash` and `/worker/tasks/claim` include `tracker_url` and `updated_at`.
  3. All tests pass with >=90% coverage.
- **Commit**: `feat(api): bypass cooldown for unupdated stats and enrich task payloads with tracker context`

## Checks

**C1** - TrackerStat fields nullability (S1.1)
Proof: `poetry run pytest tests/test_models.py -k test_tracker_stat`
**C2** - Cooldown bypass on null updated_at (S1.2, S1.5)
Proof: `poetry run pytest tests/test_api_worker.py -k test_worker_claim_scrape_stats_null_cooldown`
**C3** - Claim task payload enrichment (S1.3)
Proof: `poetry run pytest tests/test_api_worker.py -k test_worker_claim_task_payload_enrichment`
**C4** - Torrent get task status enrichment (S1.4)
Proof: `poetry run pytest tests/test_api_torrents.py -k test_get_torrent_task_enrichment`
