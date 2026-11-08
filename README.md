# torrent-stats

Resolving info hashes into .torrent files, detailed file trees, and live peer/seed stats across trackers.

## Architecture & Stack

- **API (`torrent_stats/` - Python)**: FastAPI + CouchDB (Repository pattern) + Redis (12h hourly hit buckets synced to CouchDB `totalHits`/`lastHitAt`, task leases). Agnostic storage profiles (FTP first via `fsspec`, recording profile ID and `file_path`, rendering download URLs via profile templates).
- **Worker (`worker/` - Go)**: Standalone binary communicating via authenticated HTTP API endpoints (`X-Worker-Key`) with ACK/leases and automatic tracker pruning after 3 consecutive failures.
- **API Specification**: Defined in `api/openapi.yaml`.

---

## Getting Started

### Prerequisites

- Python 3.11+ / 3.13+
- Poetry
- Go 1.21+ (for worker)
- Docker (optional)

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

### Running with Docker

1. Build the Docker image:
   ```bash
   docker build -t torrent-stats-api .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 torrent-stats-api
   ```
