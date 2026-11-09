from typing import Annotated, TypeAlias

from fastapi import Depends
from torrent_stats.db.repository import TaskRepository, TorrentMetadataRepository


def get_torrent_repository():
    return TorrentMetadataRepository()


def get_task_repository():
    return TaskRepository()


TorrentRepositoryDepends: TypeAlias = Annotated[
    TorrentMetadataRepository, Depends(get_torrent_repository)
]
TaskRepositoryDepends: TypeAlias = Annotated[
    TaskRepository, Depends(get_task_repository)
]
