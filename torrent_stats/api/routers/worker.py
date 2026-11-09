from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Annotated

import pydantic
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from torrent_stats.db.models import (
    TaskDocument,
    TorrentFile,
    TorrentMetadata,
    TrackerStat,
)
from torrent_stats.db.repository import (
    TaskRepository,
    TorrentMetadataRepository,
    WorkerKeyRepository,
)
from torrent_stats.services.storage import storage_manager
from torrent_stats.settings import worker_settings

router = APIRouter(prefix="/worker", tags=["worker"])
torrent_repo = TorrentMetadataRepository()
task_repo = TaskRepository()
worker_key_repo = WorkerKeyRepository()
logger = logging.getLogger("torrent_stats.worker")


def verify_worker_key(
    x_worker_key: Annotated[str | None, Header(alias="X-Worker-Key")] = None,
) -> str:
    if not x_worker_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Key header",
        )
    if worker_settings.worker_allow_any_key:
        return x_worker_key
    worker_key = worker_key_repo.find_by_key_hash(x_worker_key)
    if not worker_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Worker-Key",
        )
    return x_worker_key


@router.post("/tasks/claim", status_code=status.HTTP_200_OK)
def claim_task(
    response: Response,
    _: str = Depends(verify_worker_key),
):
    now = datetime.now(UTC)
    all_tasks = task_repo.find_claimable()
    logger.debug("Evaluating task claim. Total tasks in repository: %d", len(all_tasks))

    candidates: list[TaskDocument] = []
    for task in all_tasks:
        # Check failure cooldown (12h)
        if task.last_attempt_at and task.status == "failed":
            last_attempt = datetime.fromisoformat(task.last_attempt_at)
            if (
                now - last_attempt
            ).total_seconds() < worker_settings.worker_failure_cooldown_seconds:
                logger.debug(
                    "Task %s skipped: failure cooldown active (last attempt at %s).",
                    task.id,
                    task.last_attempt_at,
                )
                continue

        # Check stats update cooldown (6h) for scrape_stats tasks
        if task.task_type == "scrape_stats" and task.tracker_url:
            torrent = torrent_repo.find_by_info_hash(task.info_hash)
            if torrent and torrent.tracker_stats:
                stat = next(
                    (
                        ts
                        for ts in torrent.tracker_stats
                        if ts.tracker_url == task.tracker_url
                    ),
                    None,
                )
                if (
                    stat
                    and (now - datetime.fromisoformat(stat.updated_at)).total_seconds()
                    < worker_settings.worker_stats_cooldown_seconds
                ):
                    logger.debug(
                        "Task %s skipped: stats update cooldown active for tracker %s.",
                        task.id,
                        task.tracker_url,
                    )
                    continue

        logger.debug(
            "Task %s (type: %s) added as claim candidate.", task.id, task.task_type
        )
        candidates.append(task)

    if not candidates:
        logger.info("No claimable tasks available. Returning 204 No Content.")
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    # Prioritize scrape_torrent over scrape_stats, then by creation date
    candidates.sort(
        key=lambda x: (0 if x.task_type == "scrape_torrent" else 1, x.created_at)
    )

    task = candidates[0]
    logger.debug(
        "Selected top candidate task %s (type: %s) out of %d candidates.",
        task.id,
        task.task_type,
        len(candidates),
    )

    task.status = "claimed"
    task.claimed_at = now.isoformat()
    lease_expires = now.timestamp() + worker_settings.worker_task_lease_seconds
    task.lease_expires_at = datetime.fromtimestamp(lease_expires, UTC).isoformat()
    task.last_attempt_at = now.isoformat()

    task_repo.save(task)

    logger.info(
        "Worker successfully claimed task %s for info_hash %s (type: %s, lease expires at %s).",
        task.id,
        task.info_hash,
        task.task_type,
        task.lease_expires_at,
    )

    return {
        "task_id": task.id,
        "info_hash": task.info_hash,
        "task_type": task.task_type,
        "lease_expires_at": task.lease_expires_at,
    }


@router.post("/torrents", status_code=status.HTTP_201_CREATED)
async def upload_torrent(
    info_hash: Annotated[str, Form()],
    name: Annotated[str, Form()],
    total_size: Annotated[int, Form()],
    torrent_file: UploadFile = File(...),  # noqa: B008
    storage_profile_key: Annotated[str | None, Form()] = None,
    storage_params: Annotated[str | None, Form()] = None,
    files: Annotated[str | None, Form()] = None,
    _: str = Depends(verify_worker_key),
):
    file_bytes = await torrent_file.read()

    profile_key, computed_params, _ = storage_manager.upload_torrent(
        info_hash, file_bytes, explicit_profile_key=storage_profile_key
    )

    final_params = computed_params
    if storage_params:
        try:
            parsed_params = json.loads(storage_params)
            if isinstance(parsed_params, dict):
                final_params.update(parsed_params)
        except (json.JSONDecodeError, TypeError):
            pass

    parsed_files = None
    if files:
        try:
            files_data = json.loads(files)
            if isinstance(files_data, list):
                parsed_files = [TorrentFile.model_validate(f) for f in files_data]
        except (json.JSONDecodeError, TypeError, ValueError, pydantic.ValidationError):
            pass

    torrent = torrent_repo.find_by_info_hash(info_hash)
    if not torrent:
        torrent = TorrentMetadata(info_hash=info_hash)

    torrent.name = name
    torrent.total_size = total_size
    torrent.storage_profile_key = profile_key
    torrent.storage_params = final_params
    if parsed_files:
        torrent.files = parsed_files

    torrent_repo.save(torrent)

    tasks = task_repo.find_by_info_hash(info_hash)
    scrape_task = next((t for t in tasks if t.task_type == "scrape_torrent"), None)
    if scrape_task:
        scrape_task.status = "completed"
        task_repo.save(scrape_task)
    else:
        task_repo.save(
            TaskDocument(
                info_hash=info_hash,
                task_type="scrape_torrent",
                status="completed",
            )
        )

    return {"status": "success", "info_hash": info_hash}


class TrackerStatsSubmit(BaseModel):
    tracker_url: str
    success: bool
    seeds: int | None = 0
    peers: int | None = 0


@router.post("/torrents/{hash}/stats", status_code=status.HTTP_200_OK)
def submit_tracker_stats(
    hash: str,
    payload: TrackerStatsSubmit,
    _: str = Depends(verify_worker_key),
):
    torrent = torrent_repo.find_by_info_hash(hash)
    if not torrent:
        torrent = TorrentMetadata(info_hash=hash)

    now = datetime.now(UTC).isoformat()

    existing_stat = None
    for stat in torrent.tracker_stats:
        if stat.tracker_url == payload.tracker_url:
            existing_stat = stat
            break

    if existing_stat:
        if payload.success:
            existing_stat.seeds = payload.seeds or 0
            existing_stat.peers = payload.peers or 0
            existing_stat.updated_at = now
            existing_stat.consecutive_failures = 0
        else:
            existing_stat.consecutive_failures += 1
    else:
        if payload.success:
            torrent.tracker_stats.append(
                TrackerStat(
                    tracker_url=payload.tracker_url,
                    seeds=payload.seeds or 0,
                    peers=payload.peers or 0,
                    updated_at=now,
                    consecutive_failures=0,
                )
            )
        else:
            torrent.tracker_stats.append(
                TrackerStat(
                    tracker_url=payload.tracker_url,
                    seeds=0,
                    peers=0,
                    updated_at=now,
                    consecutive_failures=1,
                )
            )

    torrent.tracker_stats = [
        s for s in torrent.tracker_stats if s.consecutive_failures < 3
    ]

    torrent_repo.save(torrent)

    tasks = task_repo.find_by_info_hash(hash)
    stat_task = next(
        (
            t
            for t in tasks
            if t.task_type == "scrape_stats" and t.tracker_url == payload.tracker_url
        ),
        None,
    )
    if stat_task:
        stat_task.status = "completed" if payload.success else "failed"
        stat_task.last_attempt_at = now
        task_repo.save(stat_task)

    return {"status": "success", "info_hash": hash}
