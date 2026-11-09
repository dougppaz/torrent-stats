from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from torrent_stats.api.controllers.torrents import TorrentController
from torrent_stats.api.schemas import TorrentDetailResponse

router = APIRouter(prefix="/torrents", tags=["torrents"])


def get_torrent_controller() -> TorrentController:
    return TorrentController()


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
