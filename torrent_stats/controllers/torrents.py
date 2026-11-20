from __future__ import annotations

from torrent_stats.db.models import TaskDocument, TrackerStat
from torrent_stats.db.repository import TaskRepository, TorrentMetadataRepository
from torrent_stats.schemas import (
    TaskResponse,
    TorrentDetailResponse,
    TorrentFileResponse,
    TrackerStatResponse,
)
from torrent_stats.services.hit_counter import HitCounterService
from torrent_stats.services.storage import StorageManager
from torrent_stats.settings import trackers_settings


class TorrentController:
    def __init__(
        self,
        torrent_repository: TorrentMetadataRepository,
        task_repository: TaskRepository,
        hit_counter: HitCounterService,
        storage_manager: StorageManager,
    ) -> None:
        self.torrent_repository = torrent_repository
        self.task_repository = task_repository
        self.hit_counter = hit_counter
        self.storage_manager = storage_manager

    def get_torrent(
        self, hash: str, trackers: list[str] | None = None
    ) -> TorrentDetailResponse:
        total_hits, last_hit_at = self.hit_counter.record_hit(hash)
        current_request_timestamp = last_hit_at

        torrent, _ = self.torrent_repository.get_or_create(
            hash, total_hits=total_hits, last_hit_at=current_request_timestamp
        )

        existing_tasks = self.task_repository.find_by_info_hash(hash)
        if not any(t.task_type == "scrape_torrent" for t in existing_tasks):
            self.task_repository.save(
                TaskDocument(
                    info_hash=hash,
                    task_type="scrape_torrent",
                    status="pending",
                    created_at=current_request_timestamp,
                )
            )

        target_trackers = (
            trackers if trackers is not None else trackers_settings.default_trackers
        )
        if target_trackers:
            existing_tracker_urls = {ts.tracker_url for ts in torrent.tracker_stats}
            for tr in target_trackers:
                if tr not in existing_tracker_urls:
                    torrent.tracker_stats.append(
                        TrackerStat(
                            tracker_url=tr,
                            seeds=None,
                            peers=None,
                            updated_at=None,
                        )
                    )
                    if not any(
                        t.task_type == "scrape_stats" and t.tracker_url == tr
                        for t in existing_tasks
                    ):
                        self.task_repository.save(
                            TaskDocument(
                                info_hash=hash,
                                task_type="scrape_stats",
                                status="pending",
                                tracker_url=tr,
                                tracker_updated_at=None,
                                created_at=current_request_timestamp,
                            )
                        )
            self.torrent_repository.save(torrent)

        active_tasks = self.task_repository.find_by_info_hash(hash)

        download_url = None
        if torrent.storage_profile_key and torrent.storage_params:
            download_url = self.storage_manager.get_download_url(
                torrent.storage_profile_key, torrent.storage_params
            )

        return TorrentDetailResponse(
            info_hash=hash,
            name=torrent.name,
            total_size=torrent.total_size,
            storage_profile_key=torrent.storage_profile_key,
            storage_params=torrent.storage_params,
            download_url=download_url,
            total_hits=torrent.total_hits,
            last_hit_at=torrent.last_hit_at,
            files=(
                [
                    TorrentFileResponse(path=f.path, length=f.length)
                    for f in torrent.files
                ]
                if torrent.files
                else None
            ),
            tracker_stats=[
                TrackerStatResponse(
                    tracker_url=ts.tracker_url,
                    seeds=ts.seeds,
                    peers=ts.peers,
                    updated_at=ts.updated_at,
                )
                for ts in torrent.tracker_stats
            ],
            tasks=[
                TaskResponse(
                    task_id=t.id,
                    status=t.status,
                    tracker_url=t.tracker_url,
                    updated_at=t.tracker_updated_at,
                    created_at=t.created_at,
                    error_message=t.error_message,
                )
                for t in active_tasks
            ],
        )
