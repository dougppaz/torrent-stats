from __future__ import annotations

from typing import Annotated, TypeAlias

from fastapi import APIRouter, Depends, Query, status
from torrent_stats.api.depends import TaskRepositoryDepends, TorrentRepositoryDepends
from torrent_stats.api.schemas import TorrentDetailResponse
from torrent_stats.controllers.torrents import TorrentController
from torrent_stats.services.hit_counter import hit_counter_service
from torrent_stats.services.storage import storage_manager

router = APIRouter(prefix="/torrents", tags=["torrents"])


def get_torrent_controller(
    torrent_repository: TorrentRepositoryDepends,
    task_repository: TaskRepositoryDepends,
) -> TorrentController:
    return TorrentController(
        torrent_repository=torrent_repository,
        task_repository=task_repository,
        hit_counter=hit_counter_service,
        storage_manager=storage_manager,
    )


TorrentControllerDepends: TypeAlias = Annotated[
    TorrentController, Depends(get_torrent_controller)
]


@router.get(
    "/{hash}", status_code=status.HTTP_200_OK, response_model=TorrentDetailResponse
)
def get_torrent(
    hash: str,
    controller: TorrentControllerDepends,
    trackers: Annotated[
        list[str] | None, Query(description="Custom tracker URLs")
    ] = None,
):
    return controller.get_torrent(hash, trackers)
