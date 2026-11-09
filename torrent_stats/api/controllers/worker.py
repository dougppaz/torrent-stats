from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import pydantic
from fastapi import UploadFile
from torrent_stats.api.schemas import ActionSuccessResponse, TaskClaimResponse
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
from torrent_stats.services.storage import StorageManager
from torrent_stats.services.storage import storage_manager as _storage_mgr
from torrent_stats.settings import WorkerSettings
from torrent_stats.settings import worker_settings as _worker_settings

task_repo = TaskRepository()
torrent_repo = TorrentMetadataRepository()
worker_key_repo = WorkerKeyRepository()
storage_manager = _storage_mgr
worker_settings = _worker_settings
logger = logging.getLogger("torrent_stats.worker")


class TaskClaimController:
    def __init__(
        self,
        task_repo: TaskRepository | None = None,
        worker_settings: WorkerSettings | None = None,
    ) -> None:
        self.task_repo = task_repo or globals()["task_repo"]
        self.worker_settings = worker_settings or globals()["worker_settings"]

    def claim_task(self) -> TaskClaimResponse | None:
        now = datetime.now(UTC)
        all_tasks = self.task_repo.find_claimable()
        logger.debug(
            "Evaluating task claim. Total tasks in repository: %d", len(all_tasks)
        )

        candidates: list[TaskDocument] = []
        for task in all_tasks:
            # Check failure cooldown (12h)
            if task.last_attempt_at and task.status == "failed":
                last_attempt = datetime.fromisoformat(task.last_attempt_at)
                if (
                    (now - last_attempt).total_seconds()
                    < self.worker_settings.worker_failure_cooldown_seconds
                ):
                    logger.debug(
                        "Task %s skipped: failure cooldown active (last attempt at %s).",
                        task.id,
                        task.last_attempt_at,
                    )
                    continue

            # Check stats update cooldown (6h) for scrape_stats tasks using denormalized tracker_updated_at
            if (
                task.task_type == "scrape_stats"
                and task.tracker_url
                and task.tracker_updated_at is not None
            ):
                tracker_updated = datetime.fromisoformat(task.tracker_updated_at)
                if (
                    now - tracker_updated
                ).total_seconds() < self.worker_settings.worker_stats_cooldown_seconds:
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
            logger.info("No claimable tasks available.")
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
        lease_expires = now.timestamp() + self.worker_settings.worker_task_lease_seconds
        task.lease_expires_at = datetime.fromtimestamp(lease_expires, UTC).isoformat()
        task.last_attempt_at = now.isoformat()

        self.task_repo.save(task)

        logger.info(
            "Worker successfully claimed task %s for info_hash %s (type: %s, lease expires at %s).",
            task.id,
            task.info_hash,
            task.task_type,
            task.lease_expires_at,
        )

        return TaskClaimResponse(
            task_id=task.id,
            info_hash=task.info_hash,
            task_type=task.task_type,
            tracker_url=task.tracker_url,
            updated_at=task.tracker_updated_at,
            lease_expires_at=task.lease_expires_at,
        )


class TorrentUploadController:
    def __init__(
        self,
        torrent_repo: TorrentMetadataRepository | None = None,
        task_repo: TaskRepository | None = None,
        storage_manager: StorageManager | None = None,
    ) -> None:
        self.torrent_repo = torrent_repo or globals()["torrent_repo"]
        self.task_repo = task_repo or globals()["task_repo"]
        self.storage_manager = storage_manager or globals()["storage_manager"]

    async def upload_torrent(
        self,
        info_hash: str,
        name: str,
        total_size: int,
        torrent_file: UploadFile,
        storage_profile_key: str | None = None,
        storage_params: str | None = None,
        files: str | None = None,
    ) -> ActionSuccessResponse:
        file_bytes = await torrent_file.read()

        profile_key, computed_params, _ = self.storage_manager.upload_torrent(
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
            except (
                json.JSONDecodeError,
                TypeError,
                ValueError,
                pydantic.ValidationError,
            ):
                pass

        torrent = self.torrent_repo.find_by_info_hash(info_hash)
        if not torrent:
            torrent = TorrentMetadata(info_hash=info_hash)

        torrent.name = name
        torrent.total_size = total_size
        torrent.storage_profile_key = profile_key
        torrent.storage_params = final_params
        if parsed_files:
            torrent.files = parsed_files

        self.torrent_repo.save(torrent)

        tasks = self.task_repo.find_by_info_hash(info_hash)
        scrape_task = next((t for t in tasks if t.task_type == "scrape_torrent"), None)
        if scrape_task:
            scrape_task.status = "completed"
            self.task_repo.save(scrape_task)
        else:
            self.task_repo.save(
                TaskDocument(
                    info_hash=info_hash,
                    task_type="scrape_torrent",
                    status="completed",
                )
            )

        return ActionSuccessResponse(status="success", info_hash=info_hash)


class TrackerStatsController:
    def __init__(
        self,
        torrent_repo: TorrentMetadataRepository | None = None,
        task_repo: TaskRepository | None = None,
    ) -> None:
        self.torrent_repo = torrent_repo or globals()["torrent_repo"]
        self.task_repo = task_repo or globals()["task_repo"]

    def submit_stats(
        self,
        hash: str,
        tracker_url: str,
        success: bool,
        seeds: int | None = 0,
        peers: int | None = 0,
    ) -> ActionSuccessResponse:
        torrent = self.torrent_repo.find_by_info_hash(hash)
        if not torrent:
            torrent = TorrentMetadata(info_hash=hash)

        now = datetime.now(UTC).isoformat()

        existing_stat = None
        for stat in torrent.tracker_stats:
            if stat.tracker_url == tracker_url:
                existing_stat = stat
                break

        if existing_stat:
            if success:
                existing_stat.seeds = seeds or 0
                existing_stat.peers = peers or 0
                existing_stat.updated_at = now
                existing_stat.consecutive_failures = 0
            else:
                existing_stat.consecutive_failures += 1
        else:
            if success:
                torrent.tracker_stats.append(
                    TrackerStat(
                        tracker_url=tracker_url,
                        seeds=seeds or 0,
                        peers=peers or 0,
                        updated_at=now,
                        consecutive_failures=0,
                    )
                )
            else:
                torrent.tracker_stats.append(
                    TrackerStat(
                        tracker_url=tracker_url,
                        seeds=0,
                        peers=0,
                        updated_at=now,
                        consecutive_failures=1,
                    )
                )

        torrent.tracker_stats = [
            s for s in torrent.tracker_stats if s.consecutive_failures < 3
        ]

        self.torrent_repo.save(torrent)

        tasks = self.task_repo.find_by_info_hash(hash)
        stat_task = next(
            (
                t
                for t in tasks
                if t.task_type == "scrape_stats" and t.tracker_url == tracker_url
            ),
            None,
        )
        if stat_task:
            stat_task.status = "completed" if success else "failed"
            stat_task.last_attempt_at = now
            if success:
                stat_task.tracker_updated_at = now
            self.task_repo.save(stat_task)

        return ActionSuccessResponse(status="success", info_hash=hash)
