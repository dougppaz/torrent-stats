from __future__ import annotations

import json
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
from torrent_stats.db.models import TaskItem, TorrentFile, TorrentMetadata, TrackerStat
from torrent_stats.db.repository import TorrentMetadataRepository, WorkerKeyRepository
from torrent_stats.services.storage import storage_manager
from torrent_stats.settings import worker_settings

router = APIRouter(prefix="/worker", tags=["worker"])
torrent_repo = TorrentMetadataRepository()
worker_key_repo = WorkerKeyRepository()


def verify_worker_key(
    x_worker_key: Annotated[str | None, Header(alias="X-Worker-Key")] = None,
) -> str:
    if not x_worker_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Worker-Key header",
        )
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
    db = torrent_repo.client.get_db()

    candidates: list[tuple[TorrentMetadata, TaskItem]] = []
    for doc_id in db:
        if doc_id.startswith("_"):
            continue
        doc = db.get(doc_id)
        if not doc:
            continue
        try:
            torrent = TorrentMetadata.model_validate(doc)
        except (ValueError, TypeError, pydantic.ValidationError):
            continue

        for task in torrent.tasks:
            is_pending = task.status == "pending"
            is_expired_lease = (
                task.status in ("claimed", "scraping")
                and task.lease_expires_at
                and datetime.fromisoformat(task.lease_expires_at) < now
            )

            if not (is_pending or is_expired_lease):
                continue

            # Check failure cooldown (12h)
            if task.last_attempt_at and task.status == "failed":
                last_attempt = datetime.fromisoformat(task.last_attempt_at)
                if (
                    now - last_attempt
                ).total_seconds() < worker_settings.worker_failure_cooldown_seconds:
                    continue

            # Check stats update cooldown (6h) for scrape_stats tasks
            if task.task_type == "scrape_stats" and torrent.tracker_stats:
                all_fresh = all(
                    (now - datetime.fromisoformat(ts.updated_at)).total_seconds()
                    < worker_settings.worker_stats_cooldown_seconds
                    for ts in torrent.tracker_stats
                )
                if all_fresh:
                    continue

            candidates.append((torrent, task))

    if not candidates:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    # Prioritize scrape_torrent over scrape_stats, then by creation date
    candidates.sort(
        key=lambda x: (0 if x[1].task_type == "scrape_torrent" else 1, x[1].created_at)
    )

    torrent, task = candidates[0]

    task.status = "claimed"
    task.claimed_at = now.isoformat()
    lease_expires = now.timestamp() + worker_settings.worker_task_lease_seconds
    task.lease_expires_at = datetime.fromtimestamp(lease_expires, UTC).isoformat()
    task.last_attempt_at = now.isoformat()

    torrent_repo.save(torrent)

    return {
        "task_id": task.task_id,
        "info_hash": torrent.info_hash,
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

    for task in torrent.tasks:
        if task.task_type == "scrape_torrent":
            task.status = "completed"

    if not any(t.task_type == "scrape_torrent" for t in torrent.tasks):
        torrent.tasks.append(
            TaskItem(
                task_id=f"task-{info_hash}-scrape",
                task_type="scrape_torrent",
                status="completed",
            )
        )

    torrent_repo.save(torrent)
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
    return {"status": "success", "info_hash": hash}
