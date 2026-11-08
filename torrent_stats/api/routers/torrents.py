from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status
from torrent_stats.db.repository import TorrentMetadataRepository
from torrent_stats.services.hit_counter import hit_counter_service
from torrent_stats.services.storage import storage_manager

router = APIRouter(prefix="/torrents", tags=["torrents"])
torrent_repo = TorrentMetadataRepository()


@router.get("/{hash}", status_code=status.HTTP_200_OK)
def get_torrent(
    hash: str,
    trackers: Annotated[
        list[str] | None, Query(description="Custom tracker URLs")
    ] = None,
):
    total_hits, last_hit_at = hit_counter_service.record_hit(hash)
    torrent = torrent_repo.find_by_info_hash(hash)

    _ = trackers

    download_url = None
    if torrent and torrent.storage_profile_key and torrent.storage_params:
        download_url = storage_manager.get_download_url(
            torrent.storage_profile_key, torrent.storage_params
        )

    return {
        "info_hash": hash,
        "name": torrent.name if torrent else None,
        "total_size": torrent.total_size if torrent else None,
        "storage_profile_key": torrent.storage_profile_key if torrent else None,
        "storage_params": torrent.storage_params if torrent else None,
        "download_url": download_url,
        "total_hits": total_hits,
        "last_hit_at": last_hit_at,
        "files": (
            [f.model_dump() for f in torrent.files]
            if torrent and torrent.files
            else None
        ),
        "tracker_stats": [],
        "tasks": [
            {
                "task_id": f"task-{hash}",
                "status": "pending",
                "created_at": last_hit_at,
            }
        ],
    }
