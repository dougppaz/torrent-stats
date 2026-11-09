from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import Depends
from torrent_stats.db.repository import (
    TaskRepository,
    TorrentMetadataRepository,
    WorkerKeyRepository,
)


def get_torrent_repository() -> TorrentMetadataRepository:
    return TorrentMetadataRepository()


def get_task_repository() -> TaskRepository:
    return TaskRepository()


def get_worker_key_repository() -> WorkerKeyRepository:
    return WorkerKeyRepository()


TorrentRepositoryDepends: TypeAlias = Annotated[
    TorrentMetadataRepository, Depends(get_torrent_repository)
]
TaskRepositoryDepends: TypeAlias = Annotated[
    TaskRepository, Depends(get_task_repository)
]
WorkerKeyRepositoryDepends: TypeAlias = Annotated[
    WorkerKeyRepository, Depends(get_worker_key_repository)
]
