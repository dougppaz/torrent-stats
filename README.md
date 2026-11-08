# torrent-stats

Resolving info hashes into .torrent files, detailed file trees, and live peer/seed stats across trackers.

## Architecture & Stack

- **API (`torrent_stats/` - Python)**: FastAPI + CouchDB (Repository pattern) + Redis (12h hourly hit buckets synced to CouchDB `totalHits`/`lastHitAt`, task leases). Agnostic storage profiles (FTP first via `fsspec`, recording profile ID and `file_path`, rendering download URLs via profile templates).
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
