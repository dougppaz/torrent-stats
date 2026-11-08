from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status
from torrent_stats.db.models import TaskDocument, TorrentMetadata, TrackerStat
from torrent_stats.db.repository import TaskRepository, TorrentMetadataRepository
from torrent_stats.services.hit_counter import hit_counter_service
from torrent_stats.services.storage import storage_manager

router = APIRouter(prefix="/torrents", tags=["torrents"])
torrent_repo = TorrentMetadataRepository()
task_repo = TaskRepository()


@router.get("/{hash}", status_code=status.HTTP_200_OK)
def get_torrent(
    hash: str,
    trackers: Annotated[
        list[str] | None, Query(description="Custom tracker URLs")
    ] = None,
):
    total_hits, last_hit_at = hit_counter_service.record_hit(hash)
    # The current request timestamp acts as both the last hit time and the creation timestamp for enqueued tasks
    current_request_timestamp = last_hit_at

    torrent = torrent_repo.find_by_info_hash(hash)

    if not torrent:
        torrent = TorrentMetadata(
            info_hash=hash,
            total_hits=total_hits,
            last_hit_at=current_request_timestamp,
        )
        torrent_repo.save(torrent)
    else:
        torrent.total_hits = total_hits
        torrent.last_hit_at = current_request_timestamp
        torrent_repo.save(torrent)

    existing_tasks = task_repo.find_by_info_hash(hash)
    if not any(t.task_type == "scrape_torrent" for t in existing_tasks):
        task_repo.save(
            TaskDocument(
                info_hash=hash,
                task_type="scrape_torrent",
                status="pending",
                created_at=current_request_timestamp,
            )
        )

    if trackers:
        existing_tracker_urls = {ts.tracker_url for ts in torrent.tracker_stats}
        for tr in trackers:
            if tr not in existing_tracker_urls:
                torrent.tracker_stats.append(TrackerStat(tracker_url=tr))
                if not any(
                    t.task_type == "scrape_stats" and t.tracker_url == tr
                    for t in existing_tasks
                ):
                    task_repo.save(
                        TaskDocument(
                            info_hash=hash,
                            task_type="scrape_stats",
                            status="pending",
                            tracker_url=tr,
                            created_at=current_request_timestamp,
                        )
                    )
        torrent_repo.save(torrent)

    active_tasks = task_repo.find_by_info_hash(hash)

    download_url = None
    if torrent.storage_profile_key and torrent.storage_params:
        download_url = storage_manager.get_download_url(
            torrent.storage_profile_key, torrent.storage_params
        )

    return {
        "info_hash": hash,
        "name": torrent.name,
        "total_size": torrent.total_size,
        "storage_profile_key": torrent.storage_profile_key,
        "storage_params": torrent.storage_params,
        "download_url": download_url,
        "total_hits": torrent.total_hits,
        "last_hit_at": torrent.last_hit_at,
        "files": ([f.model_dump() for f in torrent.files] if torrent.files else None),
        "tracker_stats": [
            {
                "tracker_url": ts.tracker_url,
                "seeds": ts.seeds,
                "peers": ts.peers,
                "updated_at": ts.updated_at,
            }
            for ts in torrent.tracker_stats
        ],
        "tasks": [
            {
                "task_id": t.id,
                "status": t.status,
                "created_at": t.created_at,
            }
            for t in active_tasks
        ],
    }
