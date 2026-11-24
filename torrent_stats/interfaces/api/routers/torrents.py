from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import APIRouter, Depends, Query, status
from torrent_stats.controllers.torrents import TorrentController
from torrent_stats.interfaces.api.depends import (
    HitCounterServiceDepends,
    StorageManagerDepends,
    TaskRepositoryDepends,
    TorrentRepositoryDepends,
)
from torrent_stats.schemas import TorrentDetailResponse, ValidatedInfoHash

router = APIRouter(prefix="/torrents", tags=["torrents"])


def get_torrent_controller(
    torrent_repository: TorrentRepositoryDepends,
    task_repository: TaskRepositoryDepends,
    hit_counter: HitCounterServiceDepends,
    storage_manager: StorageManagerDepends,
) -> TorrentController:
    return TorrentController(
        torrent_repository=torrent_repository,
        task_repository=task_repository,
        hit_counter=hit_counter,
        storage_manager=storage_manager,
    )


TorrentControllerDepends: TypeAlias = Annotated[
    TorrentController, Depends(get_torrent_controller)
]


@router.get(
    "/{hash}", status_code=status.HTTP_200_OK, response_model=TorrentDetailResponse
)
def get_torrent(
    hash: ValidatedInfoHash,
    controller: TorrentControllerDepends,
    trackers: Annotated[
        list[str] | None, Query(description="Custom tracker URLs")
    ] = None,
    record_hit: Annotated[bool, Query(description="Whether to record a hit")] = True,
):
    return controller.get_torrent(hash, trackers, record_hit=record_hit)
