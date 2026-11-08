# torrent-stats

Resolving info hashes into .torrent files, detailed file trees, and live peer/seed stats across trackers.

## Architecture & Stack

- **API (`torrent_stats/` - Python)**: FastAPI + CouchDB (Repository pattern) + Redis (12h hourly hit buckets synced to CouchDB `total_hits`/`last_hit_at`, task leases). Agnostic storage profiles (FTP first via `fsspec`, recording profile key & storage parameters, rendering download URLs via profile templates).
- **Worker (`worker/` - Go)**: Standalone binary communicating via authenticated HTTP API endpoints (`X-Worker-Key`) with ACK/leases and automatic tracker pruning after 3 consecutive failures.
- **API Specification**: Defined in `api/openapi.yaml`.

---

## Getting Started

### Prerequisites

- Python 3.15+
- Poetry
- Go 1.21+ (for worker)
- Docker & Docker Compose

### Running Locally

1. Install Python dependencies with Poetry:
   ```bash
   poetry install
   ```

2. Run the API server:
   ```bash
   poetry run uvicorn torrent_stats.main:app --reload --port 8000
   ```

3. Access the health check:
   ```bash
   curl http://localhost:8000/health
   ```

### Running with Docker Compose (API + CouchDB + Redis)

To run the complete stack locally with Docker Compose:

```bash
docker compose up --build
```

This will spin up:
- **API** on `http://localhost:8000`
- **CouchDB** on `http://localhost:5984`
- **Redis** on `redis://localhost:6379`

### Initializing CouchDB

If running CouchDB independently or via Docker Compose for the first time, you can configure it as a single node using the provided helper script:

```bash
./scripts/setup-couchdb.sh "http://admin:admin@localhost:5984"
```

---

## Environment Variables

The API service can be configured using the following environment variables (or via a `.env` file):

| Variable | Default | Description |
| --- | --- | --- |
| `COUCHDB_URL` | `http://admin:admin@localhost:5984/` | CouchDB connection URL |
| `COUCHDB_DB_NAME` | `torrent_stats` | CouchDB database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `WORKER_FAILURE_COOLDOWN_SECONDS` | `43200` (12 hours) | Failure cooldown before retrying a failed torrent |
| `WORKER_STATS_COOLDOWN_SECONDS` | `21600` (6 hours) | Update cooldown before re-scraping tracker stats |
| `WORKER_TASK_LEASE_SECONDS` | `300` (5 minutes) | Task lease/ACK timeout for active workers |
| `WORKER_KEY_SALT` | `change-this-salt-in-production` | Salt used for secure HMAC-SHA256 hashing of worker API keys |
| `CURRENT_STORAGE_PROFILE` | `default` | Active storage profile key to use for uploads |
| `STORAGE_PROFILE_[KEY]_[PARAM]` | *none* | Dynamic storage profile configuration (e.g., `STORAGE_PROFILE_FTP_TYPE=ftp`, `STORAGE_PROFILE_FTP_URL_TEMPLATE=https://download.asdf.com/{file_path}`) |
