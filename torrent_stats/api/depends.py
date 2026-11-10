from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import Depends
from torrent_stats.db.client import CouchDBClient
from torrent_stats.db.repository import (
    TaskRepository,
    TorrentMetadataRepository,
    WorkerKeyRepository,
)
from torrent_stats.services.hit_counter import HitCounterService
from torrent_stats.services.storage import StorageManager
from torrent_stats.settings import couchdb_settings


def get_couchdb_client() -> CouchDBClient:
    return CouchDBClient()


def get_torrent_repository() -> TorrentMetadataRepository:
    return TorrentMetadataRepository(client=CouchDBClient())


def get_task_repository() -> TaskRepository:
    return TaskRepository(
        client=CouchDBClient(db_name=f"{couchdb_settings.couchdb_db_name}_tasks")
    )


def get_worker_key_repository() -> WorkerKeyRepository:
    return WorkerKeyRepository(client=CouchDBClient())


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
CouchDBClientDepends: TypeAlias = Annotated[CouchDBClient, Depends(get_couchdb_client)]
