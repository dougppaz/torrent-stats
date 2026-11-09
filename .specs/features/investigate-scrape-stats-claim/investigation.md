# Investigation: `scrape_stats` Tasks Never Claimed by Workers

## 1. Description & Context

When a client queries `GET /torrents/{hash}?trackers=udp://tracker.opentrackr.org:1337/announce`, the API successfully:
1. Records the hit in Redis.
2. Creates or updates `TorrentMetadata`.
3. Registers custom trackers in `TorrentMetadata.tracker_stats`.
4. Enqueues a `scrape_stats` `TaskDocument` with `status="pending"`.

However, when remote workers call `POST /worker/tasks/claim`, the `scrape_stats` task is never returned or claimed, even though `task-8315...-scrape_torrent` gets claimed.

## 2. Case Data & Evidence

- **API Request**: `GET /torrents/{hash}?trackers=udp://...`
- **Response tasks**:
  - `scrape_torrent`: status `claimed`
  - `scrape_stats`: status `pending`
- **Worker Claim (`POST /worker/tasks/claim`)**: Returns `204 No Content` or claims `scrape_torrent`, but never claims `scrape_stats`.

## 3. Root Cause Analysis

1. **TrackerStat Initial Timestamp**:
   When a custom tracker is registered via query parameters in `GET /torrents/{hash}`, a `TrackerStat` instance is created:
   ```python
   torrent.tracker_stats.append(TrackerStat(tracker_url=tr))
   ```
   In `TrackerStat` model (`torrent_stats/db/models.py`), `updated_at` uses a default factory:
   ```python
   updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
   ```
   This means a newly registered tracker has `updated_at` set to **now** (e.g., `2026-11-09T00:57:45Z`).

2. **Stats Update Cooldown (6h) Evaluation**:
   In `claim_task` (`torrent_stats/api/routers/worker.py`), the 6-hour stats update cooldown is evaluated for `scrape_stats` tasks:
   ```python
   if (
       stat
       and (now - datetime.fromisoformat(stat.updated_at)).total_seconds()
       < worker_settings.worker_stats_cooldown_seconds
   ):
       logger.debug("Task %s skipped: stats update cooldown active...", task.id)
       continue
   ```
   Because `stat.updated_at` was just initialized to `now` upon creation, the elapsed time is `0` seconds. Since `0 < 21600` (6 hours), the cooldown check evaluates to `True`, and **the task is skipped (`continue`)**, preventing the initial scrape of newly registered trackers.

## 4. Correction Possibilities

### Option A: Set initial `updated_at` for new trackers to a past epoch (Recommended)
When a `TrackerStat` is newly added without stats (or explicitly upon registration), set `updated_at` to epoch zero (`1970-01-01T00:00:00Z`) or `None`, so that it is immediately eligible for an initial scrape. Subsequent successful scrapes by workers will update `updated_at` to `now`, activating the 6h update cooldown.

### Option B: Distinguish between registration time and last scrape time
Add a field or check whether the tracker has ever been successfully scraped, bypassing the cooldown if `seeds == 0 and peers == 0` or if it's never been scraped.

## 5. Selected Solution

**Option A**: Initialize `updated_at` for newly registered trackers to `1970-01-01T00:00:00Z` (or a timestamp far in the past), ensuring that newly added trackers are immediately scrapeable by workers while still respecting the 6h cooldown after a successful stats update.
