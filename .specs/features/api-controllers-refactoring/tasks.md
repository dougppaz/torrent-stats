# Implementation Tasks: API Controllers Architecture & Structured Response Models

Each task is atomic, testable, and concludes with a verification gate and a git commit.

- [ ] **Task 1: Pydantic Response Models & Schemas**
  - **Gate**: Create `torrent_stats/api/schemas.py` containing Pydantic `BaseModel` response models (`TorrentDetailResponse`, `TaskResponse`, `TrackerStatResponse`, `TorrentFileResponse`, `TaskClaimResponse`, `ActionSuccessResponse`), ensuring all API response structures are typed and validated.
  - **Commit**: `feat(api): add Pydantic response models for structured API serialization`

- [ ] **Task 2: Torrent Controller & Refactored Torrent Router (`GET /torrents/:hash`)**
  - **Gate**: Implement `TorrentController` class with `__init__` receiving repository and service dependencies, refactor `torrent_stats/api/routers/torrents.py` to delegate to `TorrentController` and return `TorrentDetailResponse`. All tests in `tests/test_api_torrents.py` pass.
  - **Commit**: `refactor(api): implement TorrentController and structured Pydantic response for GET /torrents/{hash}`

- [ ] **Task 3: Worker Controllers & Refactored Worker Router (`/worker/*`)**
  - **Gate**: Implement worker controllers (`TaskClaimController`, `TorrentUploadController`, `TrackerStatsController`) with dependency injection in `__init__`, refactor `torrent_stats/api/routers/worker.py` to use controllers and structured response schemas. All tests in `tests/test_api_worker.py` pass.
  - **Commit**: `refactor(api): implement worker controllers with DI and structured Pydantic responses for /worker/* routes`

- [ ] **Task 4: Architecture Documentation Update & Final Quality Gates**
  - **Gate**: Update `docs/architecture.md` with controller details and DI patterns. Run ruff check, ruff format, mypy, and pytest with 90%+ test coverage.
  - **Commit**: `docs(arch): update architecture documentation for controller refactoring and verify quality gates`
