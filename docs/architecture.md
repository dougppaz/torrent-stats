# Architecture & Design

This document outlines the architectural structure and design patterns of **torrent-stats**, including the refactored API controller architecture and structured response models.

---

## High-Level System Architecture

```mermaid
graph TD
    Client[HTTP Client / CLI] -->|REST API| API[FastAPI Service]
    Worker[Go Worker Service] -->|Authenticated HTTP (X-Worker-Key)| API
    API -->|Hourly Buckets & Leases| Redis[(Redis Cache)]
    API -->|Repositories & Documents| CouchDB[(CouchDB NoSQL)]
    API -->|Agnostic Storage Profiles| Storage[Storage Backend (FTP / Local / S3)]
    Worker -->|Torrent Scraping & Peer Discovery| DHT[BitTorrent DHT / Trackers]
```

---

## API Layer Architecture (`torrent_stats/api/`)

The API service is built using FastAPI and follows a clean 3-tier layering pattern:

1. **Routers (`torrent_stats/api/routers/`)**:
   - Responsible for HTTP protocol handling (route definitions, path/query parameter extraction, FastAPI Dependency Injection for authentication and controller resolution).
   - Thin routers that delegate business logic execution directly to API Controllers.

2. **Controllers (`torrent_stats/api/controllers/`)**:
   - Encapsulate business logic for specific actions (e.g., `TorrentController`, `TaskClaimController`, `TorrentUploadController`, `TrackerStatsController`).
   - Implemented as classes with explicit `__init__` receiving all necessary dependencies (Repositories, Services). This enables clean separation of concerns and easy mock injection in tests.

3. **Response Schemas (`torrent_stats/api/schemas.py`)**:
   - Pydantic `BaseModel` models defining structured, typed API responses (`TorrentDetailResponse`, `TaskClaimResponse`, `ActionSuccessResponse`, etc.).
   - Replaces unstructured runtime dictionaries with strict serialization and auto-generated OpenAPI documentation.

4. **Services (`torrent_stats/services/`)**:
   - Domain and utility services (e.g., `HitCounterService` for Redis-backed 12h hit counting synced to CouchDB, `StorageManager` for fsspec-based agnostic storage profiles).

5. **Repositories & Models (`torrent_stats/db/`)**:
   - CouchDB Python repository pattern (`TorrentMetadataRepository`, `TaskRepository`, `WorkerKeyRepository`) managing persistence of metadata, tasks, tracker stats, and worker keys.

---

## Worker Service Architecture (`worker/`)

- Standalone Go binary.
- Communicates exclusively via authenticated HTTP API endpoints using HMAC-SHA256 salted worker keys (`X-Worker-Key` header).
- Claims tasks via `POST /worker/tasks/claim`, enforcing 12h failure cooldowns and 6h update cooldowns.
- Submits raw `.torrent` files and stats, with automatic tracker pruning after 3 consecutive failures.

---

## Agnostic Storage Profiles

- Managed via `fsspec` backends (`local`, `ftp`, `s3` / `s3fs`).
- Stores `storage_profile_key` and `storage_params` dictionary on `TorrentMetadata`.
- Generates public download URLs dynamically via profile templates.
