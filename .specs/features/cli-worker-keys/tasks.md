# CLI Worker Key Management Tasks

**Status**: Approved
**Approved**: 2026-11-07 - user: "yes"

## Test Coverage Matrix

| Code Layer | Required Test Type | Minimum Coverage |
| --- | --- | --- |
| CLI Module (`torrent_stats/__main__.py`) | unit | 90% |

## Gate Check Commands

| Type | Command |
| --- | --- |
| Quick | `poetry run pytest tests/test_cli.py` |
| Full | `poetry run pytest` |
| Build | `poetry run ruff check torrent_stats/ tests/ && poetry run ruff format --check torrent_stats/ tests/ && poetry run mypy torrent_stats/ && poetry run pytest --cov-fail-under=90` |

## Execution Plan

### Phase 1: CLI Foundation & Commands
- **T1: CLI Entrypoint & Worker Key Commands** (`torrent_stats/__main__.py`, `tests/test_cli.py`)
  - Depends on: none
  - Tests: unit
  - Gate: Build

**Build**: `poetry run ruff check torrent_stats/ tests/ && poetry run ruff format --check torrent_stats/ tests/ && poetry run mypy torrent_stats/ && poetry run pytest --cov-fail-under=90`

## Task Breakdown

### T1: CLI Entrypoint & Worker Key Commands

- **Scope**: Implement `python -m torrent_stats` entrypoint with `workers create`, `workers list`, and `workers delete` commands using `argparse` and `WorkerKeyRepository`.
- **Where**: `torrent_stats/__main__.py`, `tests/test_cli.py`
**Tests**: unit
**Gate**: Build
- **Done when**:
  1. `python -m torrent_stats workers create --description "Test"` generates and prints raw key, exits 0.
  2. `python -m torrent_stats workers list` lists keys, exits 0.
  3. `python -m torrent_stats workers delete <id>` deletes key, exits 0 (or 1 if missing).
  4. Unit tests in `tests/test_cli.py` pass with >=90% coverage.
- **Commit**: `feat(cli): implement worker key cli commands and tests`

## Checks

**C1** - worker key create works (S1.1)
Proof: `poetry run pytest tests/test_cli.py -k test_cli_workers_create`
**C2** - worker key list works (S1.2)
Proof: `poetry run pytest tests/test_cli.py -k test_cli_workers_list`
**C3** - worker key delete works (S1.3)
Proof: `poetry run pytest tests/test_cli.py -k test_cli_workers_delete`
**C4** - worker key delete not found works (S1.4)
Proof: `poetry run pytest tests/test_cli.py -k test_cli_workers_delete_not_found`
**C5** - cli no args works (S1.5)
Proof: `poetry run pytest tests/test_cli.py -k test_cli_no_args`
