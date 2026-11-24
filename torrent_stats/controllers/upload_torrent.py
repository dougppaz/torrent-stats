from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import pydantic
from fastapi import UploadFile

from torrent_stats.db.models import TaskDocument, TorrentFile, TorrentMetadata
from torrent_stats.db.repository import TaskRepository, TorrentMetadataRepository
from torrent_stats.schemas import ActionSuccessResponse
from torrent_stats.services.storage import StorageManager

logger = logging.getLogger("torrent_stats.worker")


class TorrentUploadController:
    def __init__(
        self,
        torrent_repository: TorrentMetadataRepository,
        task_repository: TaskRepository,
        storage_manager: StorageManager,
    ) -> None:
        self.torrent_repo = torrent_repository
        self.task_repo = task_repository
        self.storage_manager = storage_manager

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
        now = datetime.now(UTC)
        if scrape_task:
            scrape_task.status = "completed"
            scrape_task.updated_at = now
            self.task_repo.save(scrape_task)
        else:
            self.task_repo.save(
                TaskDocument(
                    info_hash=info_hash,
                    task_type="scrape_torrent",
                    status="completed",
                    updated_at=now,
                )
            )

        return ActionSuccessResponse(status="success", info_hash=info_hash)
