# Implementation Tasks: Core Resolution and Storage API

Each task is atomic, testable, and concludes with a verification gate and a git commit.

- [x] **Task 1: Python Project Setup & Dependencies**
  - **Gate**: Dependencies configured in `pyproject.toml` (Poetry), FastAPI app initialized, domain settings configured (`AppSettings`, `CouchDBSettings`, `RedisSettings`, `WorkerSettings`, `TrackersSettings`, `StorageProfilesSettings`).
  - **Commit**: `feat(api): initialize FastAPI project setup and environment configuration`

- [x] **Task 2: CouchDB Repository Abstraction & Crypto**
  - **Gate**: CouchDB repository abstraction using `couchdb-python` supporting `TorrentMetadata` (snake_case fields, `storage_params`) and hashed `WorkerKey` (HMAC-SHA256 with salt).
  - **Commit**: `feat(api): implement CouchDB storage repository abstraction and salted worker key hashing`

- [x] **Task 3: Redis Hit Counter & Sliding Window Sync**
  - **Gate**: Hourly-bucketed Redis hit tracking (12h TTL sliding window) synced to CouchDB `total_hits` and `last_hit_at` upon calling `GET /torrents/{hash}`.
  - **Commit**: `feat(api): implement Redis sliding-window hit counter and CouchDB synchronization`

- [x] **Task 4: Agnostic Storage Manager (fsspec / FTP)**
  - **Gate**: Storage manager integrating active storage profile configuration (`STORAGE_PROFILE_*`), handling `.torrent` file upload via fsspec FTP, and rendering public `download_url` via template string formatting with `storage_params`.
  - **Commit**: `feat(api): implement fsspec-inspired storage manager with FTP profile and download URL rendering`

- [x] **Task 5: Public API Endpoints (`GET /torrents/:hash`)**
  - **Gate**: Implements `GET /torrents/:hash` returning 200 OK (with metadata, download URL, tracker stats, task statuses), recording sliding-window hits, auto-enqueuing missing hashes, and registering custom trackers via query params.
  - **Commit**: `feat(api): implement public GET /torrents/:hash endpoint with hit tracking and auto-enqueue`

- [ ] **Task 6: Worker API Endpoints & Task Leasing (`/worker/*`)**
  - **Gate**: Implements authenticated worker endpoints (`POST /worker/tasks/claim` with 12h failure cooldown, 6h stats update cooldown, and lease/ACKs; `POST /worker/torrents` raw file upload; `POST /worker/torrents/{hash}/stats` with 3-consecutive-failure tracker pruning).
  - **Commit**: `feat(api): implement authenticated /worker/ endpoints, task leasing, and tracker pruning logic`
