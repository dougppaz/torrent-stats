from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import Depends
from torrent_stats.controllers import TaskFailureController
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
    return CouchDBClient(db_name=couchdb_settings.couchdb_db_name)


def get_tasks_couchdb_client() -> CouchDBClient:
    return CouchDBClient(db_name=couchdb_settings.couchdb_tasks_db_name)


CouchDBClientDepends: TypeAlias = Annotated[CouchDBClient, Depends(get_couchdb_client)]
TasksCouchDBClientDepends: TypeAlias = Annotated[
    CouchDBClient, Depends(get_tasks_couchdb_client)
]


def get_torrent_repository(
    client: CouchDBClientDepends,
) -> TorrentMetadataRepository:
    return TorrentMetadataRepository(client=client)


def get_task_repository(
    client: TasksCouchDBClientDepends,
) -> TaskRepository:
    return TaskRepository(client=client)


def get_worker_key_repository(
    client: CouchDBClientDepends,
) -> WorkerKeyRepository:
    return WorkerKeyRepository(client=client)


def get_hit_counter_service() -> HitCounterService:
    return HitCounterService()


def get_storage_manager() -> StorageManager:
    return StorageManager()


def get_task_failure_controller(
    task_repository: TaskRepositoryDepends,
) -> TaskFailureController:
    return TaskFailureController(task_repository=task_repository)


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
TaskFailureControllerDepends: TypeAlias = Annotated[
    TaskFailureController, Depends(get_task_failure_controller)
]
