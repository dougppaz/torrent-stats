from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import Depends
from torrent_stats.db.repository import (
    TaskRepository,
    TorrentMetadataRepository,
    WorkerKeyRepository,
)
from torrent_stats.services.hit_counter import HitCounterService
from torrent_stats.services.storage import StorageManager


def get_torrent_repository() -> TorrentMetadataRepository:
    return TorrentMetadataRepository()


def get_task_repository() -> TaskRepository:
    return TaskRepository()


def get_worker_key_repository() -> WorkerKeyRepository:
    return WorkerKeyRepository()


def get_hit_counter_service() -> HitCounterService:
    return HitCounterService()


def get_storage_manager() -> StorageManager:
    return StorageManager()


TorrentRepositoryDepends: TypeAlias = Annotated[
    TorrentMetadataRepository, Depends(get_torrent_repository)
]
TaskRepositoryDepends: TypeAlias = Annotated[
    TaskRepository, Depends(get_task_repository)
]
WorkerKeyRepositoryDepends: TypeAlias = Annotated[
    WorkerKeyRepository, Depends(get_worker_key_repository)
]
HitCounterServiceDepends: TypeAlias = Annotated[
    HitCounterService, Depends(get_hit_counter_service)
]
StorageManagerDepends: TypeAlias = Annotated[
    StorageManager, Depends(get_storage_manager)
]
