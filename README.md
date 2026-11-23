# torrent-stats

Resolving info hashes into .torrent files, detailed file trees, and live peer/seed stats across trackers.

## Architecture & Stack

- **API (`torrent_stats/` - Python)**: FastAPI + CouchDB (Repository pattern) + Redis (12h hourly hit buckets synced to CouchDB `total_hits`/`last_hit_at`, task leases). Agnostic storage profiles (Local storage default via `fsspec`, recording profile key & storage parameters, rendering download URLs via absolute local paths or profile templates).
- **Worker (`worker/` - Go)**: Standalone binary communicating via authenticated HTTP API endpoints (`X-Worker-Key`) with ACK/leases and automatic tracker pruning after 3 consecutive failures.
- **API Specification**: Defined in `api/openapi.json`.

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
   poetry run uvicorn torrent_stats.interfaces.api.main:app --reload --port 8000
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

### Running the Worker (`worker/`)

1. Build the Go worker binary (use `GOAMD64=v1` for maximum compatibility with older x86_64 CPUs, or `GOAMD64=v2` for optimized x86-64-v2 instructions):
   ```bash
   cd worker
   # For maximum compatibility (v1)
   GOAMD64=v1 go build -o torrent-stats-worker .
   
   # Or for v2 optimized instruction set
   GOAMD64=v2 go build -o torrent-stats-worker .
   ```

2. Run the worker binary (either via environment variables or command-line arguments, with arguments taking precedence):
   ```bash
   # Using command-line arguments
   ./worker/torrent-stats-worker --api-url "http://localhost:8000" --worker-key "your-worker-key" --claim-interval "10s"

   # Or using environment variables
   export TORRENT_STATS_API_URL="http://localhost:8000"
   export TORRENT_STATS_WORKER_KEY="your-worker-key"
   export TORRENT_STATS_CLAIM_INTERVAL="30s"
   ./worker/torrent-stats-worker
   ```

---

## Environment Variables

The API service can be configured using the following environment variables (or via a `.env` file):

| Variable | Default | Description |
| --- | --- | --- |
| `COUCHDB_URL` | `http://admin:admin@localhost:5984/` | CouchDB connection URL |
| `COUCHDB_DB_NAME` | `torrent_stats` | CouchDB database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `WORKER_SCRAPE_STATS_FAILURE_COOLDOWN_SECONDS` | `10800` (3 hours) | Failure cooldown before retrying a failed tracker stats scrape task |
| `WORKER_SCRAPE_TORRENT_FAILURE_COOLDOWN_SECONDS` | `3600` (1 hour) | Failure cooldown before retrying a failed torrent scrape task |
| `WORKER_SCRAPE_STATS_COOLDOWN_SECONDS` | `1800` (30 minutes) | Update cooldown before re-scraping tracker stats |
| `WORKER_TASK_LEASE_SECONDS` | `300` (5 minutes) | Task lease/ACK timeout for active workers |
| `WORKER_KEY_SALT` | `change-this-salt-in-production` | Salt used for secure HMAC-SHA256 hashing of worker API keys |
| `CURRENT_STORAGE_PROFILE` | `default` | Active storage profile key to use for uploads |
| `STORAGE_PROFILE_[KEY]_[PARAM]` | *none* | Dynamic storage profile configuration (e.g., `STORAGE_PROFILE_LOCAL_TYPE=local`, `STORAGE_PROFILE_LOCAL_TARGET_PATH_TEMPLATE=.torrents/{info_hash}.torrent`) |

### Storage Profiles Configuration

Storage backends (`local`, `ftp`, `s3` / `s3fs`) are managed via `fsspec` and configured via environment variables:

- **Local Storage**:
  ```env
  STORAGE_PROFILE_DEFAULT_TYPE=local
  STORAGE_PROFILE_DEFAULT_TARGET_PATH_TEMPLATE=.torrents/{info_hash}.torrent
  ```
- **FTP Storage**:
  ```env
  STORAGE_PROFILE_FTP_TYPE=ftp
  STORAGE_PROFILE_FTP_HOST=ftp.example.com
  STORAGE_PROFILE_FTP_USERNAME=user
  STORAGE_PROFILE_FTP_PASSWORD=pass
  STORAGE_PROFILE_FTP_TARGET_PATH_TEMPLATE=/torrents/{info_hash}.torrent
  STORAGE_PROFILE_FTP_DOWNLOAD_URL_TEMPLATE=ftp://user:pass@ftp.example.com/torrents/{info_hash}.torrent
  ```
- **S3 / S3-compatible Storage (AWS S3, MinIO, LocalStack)**:
  *(Note: `STORAGE_PROFILE_S3_BUCKET` is used to interpolate `{bucket}` in path and download URL templates)*
  ```env
  STORAGE_PROFILE_S3_TYPE=s3
  STORAGE_PROFILE_S3_BUCKET=my-torrent-bucket
  STORAGE_PROFILE_S3_KEY=your-aws-access-key
  STORAGE_PROFILE_S3_SECRET=your-aws-secret-key
  STORAGE_PROFILE_S3_ENDPOINT_URL=https://s3.amazonaws.com # or http://localhost:9000 for MinIO
  STORAGE_PROFILE_S3_REGION_NAME=us-east-1
  STORAGE_PROFILE_S3_TARGET_PATH_TEMPLATE={bucket}/torrents/{info_hash}.torrent
  STORAGE_PROFILE_S3_DOWNLOAD_URL_TEMPLATE=https://{bucket}.s3.amazonaws.com/{target_path}
  ```

### Worker Configuration (`worker/`)

The remote worker can be configured using environment variables or command-line arguments (where terminal arguments take priority over environment variables):

| Environment Variable | Command-Line Flag | Default | Description |
| --- | --- | --- | --- |
| `TORRENT_STATS_API_URL` | `--api-url` / `-u` | *(Required)* | Torrent Stats API base URL |
| `TORRENT_STATS_WORKER_KEY` | `--worker-key` / `-k` | *(Required)* | Worker authentication key (`X-Worker-Key`) |
| `TORRENT_STATS_CLAIM_INTERVAL` | `--claim-interval` / `-i` | `30s` | Polling interval for claiming tasks |
| `TORRENT_STATS_SCRAPE_TIMEOUT` | `--scrape-timeout` | `4m` | Timeout for scraping torrent metadata from DHT/trackers |
