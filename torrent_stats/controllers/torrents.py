from __future__ import annotations

from datetime import UTC, datetime

from torrent_stats.db.models import TaskDocument
from torrent_stats.db.repository import (
    TaskRepository,
    TorrentMetadataRepository,
    TrackerStatsRepository,
)
from torrent_stats.schemas import (
    TaskResponse,
    TorrentDetailResponse,
    TorrentFileResponse,
    TrackerStatResponse,
)
from torrent_stats.services.hit_counter import HitCounterService
from torrent_stats.services.storage import StorageManager
from torrent_stats.settings import trackers_settings, worker_settings


class TorrentController:
    def __init__(
        self,
        torrent_repository: TorrentMetadataRepository,
        task_repository: TaskRepository,
        tracker_stats_repository: TrackerStatsRepository,
        hit_counter: HitCounterService,
        storage_manager: StorageManager,
    ) -> None:
        self.torrent_repository = torrent_repository
        self.task_repository = task_repository
        self.tracker_stats_repo = tracker_stats_repository
        self.hit_counter = hit_counter
        self.storage_manager = storage_manager

    def get_torrent(
        self, hash: str, trackers: list[str] | None = None, record_hit: bool = True
    ) -> TorrentDetailResponse:
        total_hits, last_hit_at = self.hit_counter.record_hit(
            hash, record_hit=record_hit
        )
        current_request_timestamp = datetime.now(UTC)

        torrent, _ = self.torrent_repository.get_or_create(hash)

        now = datetime.now(UTC)
        existing_tasks = self.task_repository.find_by_info_hash(hash)

        # Scrape torrent task management and renewal
        active_scrape_torrent = next(
            (
                t
                for t in existing_tasks
                if t.task_type == "scrape_torrent"
                and t.status in ("pending", "claimed", "scraping")
            ),
            None,
        )
        if not active_scrape_torrent:
            latest_scrape_torrent = next(
                (t for t in existing_tasks if t.task_type == "scrape_torrent"), None
            )
            should_create_torrent = False
            if not latest_scrape_torrent or (
                latest_scrape_torrent.status == "failed"
                and latest_scrape_torrent.last_attempt_at
                and (now - latest_scrape_torrent.last_attempt_at).total_seconds()
                >= worker_settings.worker_scrape_torrent_failure_cooldown_seconds
            ):
                should_create_torrent = True

            if should_create_torrent:
                self.task_repository.save(
                    TaskDocument(
                        info_hash=hash,
                        task_type="scrape_torrent",
                        status="pending",
                        created_at=current_request_timestamp,
                    )
                )

        combined_trackers = set(trackers_settings.default_trackers)
        if trackers is not None:
            combined_trackers.update(trackers)

        existing_tracker_docs = self.tracker_stats_repo.find_by_info_hash(hash)
        if combined_trackers:
            existing_tracker_urls = {ts.tracker_url for ts in existing_tracker_docs}
            for tr in combined_trackers:
                if tr not in existing_tracker_urls:
                    self.tracker_stats_repo.get_or_create(hash, tr)
            existing_tracker_docs = self.tracker_stats_repo.find_by_info_hash(hash)

        all_tracker_urls = {ts.tracker_url for ts in existing_tracker_docs}
        for tr in all_tracker_urls:
            active_stat_task = next(
                (
                    t
                    for t in existing_tasks
                    if t.task_type == "scrape_stats"
                    and t.tracker_url == tr
                    and t.status in ("pending", "claimed", "scraping")
                ),
                None,
            )
            if not active_stat_task:
                latest_stat_task = next(
                    (
                        t
                        for t in existing_tasks
                        if t.task_type == "scrape_stats" and t.tracker_url == tr
                    ),
                    None,
                )
                should_create_stat = False
                if not latest_stat_task:
                    should_create_stat = True
                elif latest_stat_task.status in ("completed", "failed"):
                    ref_dt = (
                        latest_stat_task.tracker_updated_at
                        or latest_stat_task.last_attempt_at
                        or latest_stat_task.updated_at
                        or latest_stat_task.created_at
                    )
                    should_renew = True
                    if ref_dt and (
                        (now - ref_dt).total_seconds()
                        < worker_settings.worker_scrape_stats_cooldown_seconds
                    ):
                        should_renew = False
                    if should_renew:
                        should_create_stat = True

                if should_create_stat:
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
            total_hits=total_hits,
            last_hit_at=last_hit_at,
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
                for ts in existing_tracker_docs
            ],
            tasks=[
                TaskResponse(
                    task_id=t.id,
                    task_type=t.task_type,
                    status=t.status,
                    tracker_url=t.tracker_url,
                    updated_at=t.updated_at
                    or t.tracker_updated_at
                    or t.last_attempt_at,
                    created_at=t.created_at,
                    error_message=t.error_message,
                )
                for t in active_tasks
            ],
        )
