from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from torrent_stats.api.controllers.torrents import TorrentController
from torrent_stats.api.schemas import TorrentDetailResponse
from torrent_stats.db.repository import TaskRepository, TorrentMetadataRepository
from torrent_stats.services.hit_counter import (
    hit_counter_service as _hit_counter_svc,
)
from torrent_stats.services.storage import storage_manager as _storage_mgr

router = APIRouter(prefix="/torrents", tags=["torrents"])

torrent_repo = TorrentMetadataRepository()
task_repo = TaskRepository()
hit_counter_service = _hit_counter_svc
storage_manager = _storage_mgr


def get_torrent_controller() -> TorrentController:
    return TorrentController(
        torrent_repo=torrent_repo,
        task_repo=task_repo,
        hit_counter=hit_counter_service,
        storage_manager=storage_manager,
    )


@router.get(
    "/{hash}", status_code=status.HTTP_200_OK, response_model=TorrentDetailResponse
)
def get_torrent(
    hash: str,
    trackers: Annotated[
        list[str] | None, Query(description="Custom tracker URLs")
    ] = None,
    controller: TorrentController = Depends(get_torrent_controller),  # noqa: B008
):
    return controller.get_torrent(hash, trackers)
