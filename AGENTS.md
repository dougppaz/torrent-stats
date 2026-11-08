# AGENTS.md

Instructions for coding agents working on **torrent-stats**.

## Architecture Overview

- **API Service (`torrent_stats/` - Python)**:
  - Built with Python (FastAPI recommended).
  - Primary database: CouchDB using an agnostic repository pattern (prepared for MongoDB/others).
  - Cache & Counters: Redis (12-hour hourly hit buckets synced to CouchDB `totalHits`/`lastHitAt`, task leases, and stats).
  - Agnostic Storage: fsspec-inspired storage profiles (FTP implementation first) recording profile ID and file path, with public download URL templates (e.g., `https://download.asdf.com/{file_path}`).
  - Endpoints defined in `api/openapi.yaml`.

- **Worker Service (`worker/` - Go)**:
  - Built with Go for easy binary distribution.
  - Communicates exclusively via authenticated HTTP API endpoints (`X-Worker-Key` header).
  - Claims tasks via `POST /worker/tasks/claim` (respecting 12h failure cooldowns and 6h stats update cooldowns, with ACK/leases).
  - Uploads raw `.torrent` files and submits stats/failures (pruning trackers after 3 consecutive failures).

## Specifications & Standards

- Feature plan: `.specs/features/core-resolution/plan.md` (Approved: `user: "yes"`).
- API Spec: `api/openapi.yaml`.
- All changes must conform to active decisions in `.specs/STATE.md` (if any) and the approved plan.
