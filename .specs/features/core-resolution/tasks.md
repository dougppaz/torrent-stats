# Implementation Tasks: Core Resolution and Storage API

Each task is atomic, testable, and concludes with a verification gate and a git commit.

- [x] **Task 1: Python Project Setup & Dependencies**
  - **Gate**: Dependencies configured in `pyproject.toml`, FastAPI app initialized, environment config loaded.
  - **Commit**: `feat(api): initialize FastAPI project setup and environment configuration`

- [x] **Task 2: CouchDB Repository Abstraction**
  - **Gate**: Pluggable repository pattern for CouchDB supporting `TorrentMetadata`, `StorageProfile`, and `WorkerKey` models.
  - **Commit**: `feat(api): implement CouchDB storage repository abstraction`

- [ ] **Task 3: Redis Hit Counter & Task Leasing**
  - **Gate**: Hourly-bucketed Redis hit tracking (12h TTL sliding window) synced to CouchDB `totalHits`/`lastHitAt`, plus task lease mechanics.
  - **Commit**: `feat(api): implement Redis sliding-window hit counter and task lease management`

- [ ] **Task 4: Agnostic Storage Manager (fsspec / FTP)**
  - **Gate**: Agnostic storage profile loader (FTP implementation) handling raw file upload, recording profile ID and `filePath`, and generating public download URLs via profile templates.
  - **Commit**: `feat(api): implement fsspec-inspired storage manager with FTP profile and URL templates`

- [ ] **Task 5: Public API Endpoints (`GET /torrents/:hash`)**
  - **Gate**: Implements `GET /torrents/:hash` returning 200 OK (with metadata, download URL, tracker stats, task statuses), recording sliding-window hits, auto-enqueuing missing hashes, and registering custom trackers.
  - **Commit**: `feat(api): implement public GET /torrents/:hash endpoint with hit tracking and auto-enqueue`

- [ ] **Task 6: Worker API Endpoints (`/worker/*`)**
  - **Gate**: Implements authenticated worker endpoints (`POST /worker/tasks/claim` with 12h/6h cooldowns and leases, `POST /worker/torrents` raw file upload, `POST /worker/torrents/:hash/stats` with 3-failure tracker pruning).
  - **Commit**: `feat(api): implement authenticated /worker/ endpoints and tracker pruning logic`
