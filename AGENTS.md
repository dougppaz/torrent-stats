# AGENTS.md

Instructions for coding agents working on **torrent-stats**.

## Environment & Tooling

- **asdf-vm**: Manages tool versions (`.tool-versions`). Ensure correct Python and Go runtimes via asdf.
- **Python / Poetry (`torrent_stats/` - API)**: FastAPI + CouchDB (Repository pattern) + Redis (12h hourly hit buckets synced to CouchDB `totalHits`/`lastHitAt`, task leases). Agnostic storage profiles (FTP first via `fsspec`, recording profile ID and `file_path`, rendering download URLs via profile templates like `https://download.asdf.com/{file_path}`). Routes defined in `api/openapi.yaml`.
- **Go (`worker/` - Worker)**: Standalone binary. Communicates exclusively via authenticated HTTP API endpoints (`X-Worker-Key`). Claims tasks via `POST /worker/tasks/claim` enforcing 12h failure cooldowns (new torrents) and 6h update cooldowns (tracker stats), with ACK/leases and automatic tracker pruning after 3 consecutive failures.

## Directives

- **Specifications are binding**: Feature shape and acceptance criteria live in `.specs/features/core-resolution/plan.md` (Approved: `user: "yes"`). API contracts live in `api/openapi.yaml`.
- **Atomic implementation**: Build strictly slice by slice. Verify every check against the plan.
