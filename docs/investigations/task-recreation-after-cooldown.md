# Investigation: Torrent Scrape and Stats Tasks Not Being Recreated After Cooldown

## 1. Description & Context

When torrent metadata and tracker stats are queried via `GET /torrents/{hash}` or processed by workers, tasks (`scrape_torrent` and `scrape_stats`) are created in CouchDB (`torrent_stats_tasks`).
When a task fails (e.g., `scrape_torrent` failing with `unexpected status code for torrent upload: 500`, or `scrape_stats` failing due to network/timeout), it transitions to `status="failed"`.

As observed on `https://torrent-stats.dgls.me/torrents/0303d6b36e08956494c47cd94c4b4b7542988c78`, tasks that failed hours or days ago (well exceeding the environment cooldowns `WORKER_STATS_COOLDOWN_SECONDS=3600` and `WORKER_FAILURE_COOLDOWN_SECONDS=10800`) are **never recreated or re-attempted**, leaving the torrent in a permanently failed/stale task state.

## 2. Case Data & Evidence

Inspecting `https://torrent-stats.dgls.me/torrents/0303d6b36e08956494c47cd94c4b4b7542988c78`:
- **`scrape_torrent` task**:
  - `status`: `"failed"`
  - `created_at`: `2026-11-22T02:02:24.487615+00:00`
  - `updated_at`: `2026-11-22T02:02:36.213202+00:00`
  - `error_message`: `"failed to upload torrent: unexpected status code for torrent upload: 500"`
- **`scrape_stats` task for `udp://exodus.desync.com:6969/announce`**:
  - `status`: `"failed"`
  - `created_at`: `2026-11-22T02:02:24.487615+00:00`
  - `updated_at`: `2026-11-22T02:05:33.179958+00:00`
  - `error_message`: `"read udp [...]: i/o timeout"`
- **Observation**: Despite hours passing (exceeding 3h stats cooldown and 3h/12h failure cooldown), no new task has been created or claimed.

## 3. Root Cause Analysis

1. **Existence Check Prevents Recreation (`TorrentController.get_torrent`)**:
   In `torrent_stats/controllers/torrents.py`:
   ```python
   existing_tasks = self.task_repository.find_by_info_hash(hash)
   if not any(t.task_type == "scrape_torrent" for t in existing_tasks):
       self.task_repository.save(
           TaskDocument(
               info_hash=hash,
               task_type="scrape_torrent",
               status="pending",
               created_at=current_request_timestamp,
           )
       )
   ```
   And similarly for `scrape_stats`:
   ```python
   if not any(
       t.task_type == "scrape_stats" and t.tracker_url == tr
       for t in existing_tasks
   ):
       self.task_repository.save(...)
   ```
   The controller checks whether **any** task of that type/tracker exists, regardless of its status (`completed`, `failed`, etc.). Once a task fails, it stays in the database with `status="failed"`. Consequently, `any(...)` returns `True`, preventing any new task from ever being created.

2. **Claimable Tasks View Excludes Failed Tasks (`TaskRepository.find_claimable`)**:
   In `torrent_stats/db/repository.py`, `find_claimable()` queries the CouchDB view `tasks/claimable`, which only indexes and returns documents where `status` is `"pending"`, `"claimed"`, or `"scraping"`:
   ```javascript
   function(doc) {
       if (doc.status) {
           var lease = doc.lease_expires_at ? doc.lease_expires_at : "";
           emit([doc.status, lease], null);
       }
   }
   ```
   It completely omits documents with `status="failed"` (or `"completed"`).
   Therefore, even though `TaskClaimController` contains conditional logic to evaluate failure cooldowns (`task.last_attempt_at and task.status == "failed"`), failed tasks are never returned by `find_claimable()` in the first place.

## 4. Correction Possibilities

### Option A: Reset or Recreate Failed Tasks upon Cooldown Expiration / New Request
When `GET /torrents/{hash}` is called (or during task claim evaluation), check if existing tasks for `scrape_torrent` or `scrape_stats` are in a `failed` state and whether their failure cooldown (or stats update cooldown) has expired. If expired, either reset their status to `"pending"` (updating timestamps/clearing error) or create a new task document / retry attempt.

### Option B: Include Failed Tasks in Claimable Query and Reset Status on Claim
Update `tasks/claimable` view (or `find_claimable()`) to include `"failed"` tasks whose failure cooldown has elapsed, allowing workers to claim them directly and update their status.

### Option C: Intelligent Task Lifecycle / Retry Policy
Maintain task history or allow multiple task attempts / task recreation when a task fails and the cooldown period (`WORKER_FAILURE_COOLDOWN_SECONDS` or `WORKER_STATS_COOLDOWN_SECONDS`) has elapsed.

## 5. Next Steps

Do not implement changes yet per user instruction. Once approved, select and implement the appropriate remediation strategy (e.g., allowing task recreation or status reset in `TorrentController` and/or `TaskRepository` when failure/stats cooldowns are fulfilled).
