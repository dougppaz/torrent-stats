from __future__ import annotations

from datetime import UTC, datetime

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
from torrent_stats.settings import trackers_settings, worker_settings


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
        self, hash: str, trackers: list[str] | None = None, record_hit: bool = True
    ) -> TorrentDetailResponse:
        total_hits, last_hit_at = self.hit_counter.record_hit(
            hash, record_hit=record_hit
        )
        if isinstance(last_hit_at, datetime):
            current_request_timestamp = last_hit_at.isoformat()
        elif isinstance(last_hit_at, str):
            current_request_timestamp = last_hit_at
        else:
            current_request_timestamp = datetime.now(UTC).isoformat()

        resp_last_hit = (
            last_hit_at.isoformat()
            if isinstance(last_hit_at, datetime)
            else last_hit_at
        )

        torrent, _ = self.torrent_repository.get_or_create(
            hash, total_hits=total_hits, last_hit_at=current_request_timestamp
        )

        now = datetime.now(UTC)
        existing_tasks = self.task_repository.find_by_info_hash(hash)

        # Scrape torrent task management and renewal
        scrape_torrent_task = next(
            (t for t in existing_tasks if t.task_type == "scrape_torrent"), None
        )
        if not scrape_torrent_task:
            self.task_repository.save(
                TaskDocument(
                    info_hash=hash,
                    task_type="scrape_torrent",
                    status="pending",
                    created_at=current_request_timestamp,
                )
            )
        elif (
            scrape_torrent_task.status == "failed"
            and scrape_torrent_task.last_attempt_at
        ):
            try:
                last_attempt = datetime.fromisoformat(
                    scrape_torrent_task.last_attempt_at
                )
                if (
                    (now - last_attempt).total_seconds()
                    >= worker_settings.worker_scrape_torrent_failure_cooldown_seconds
                ):
                    self.task_repository.delete(scrape_torrent_task.id)
                    self.task_repository.save(
                        TaskDocument(
                            info_hash=hash,
                            task_type="scrape_torrent",
                            status="pending",
                            created_at=current_request_timestamp,
                        )
                    )
            except (ValueError, TypeError):
                pass

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
            self.torrent_repository.save(torrent)

        all_tracker_urls = {ts.tracker_url for ts in torrent.tracker_stats}
        for tr in all_tracker_urls:
            stat_task = next(
                (
                    t
                    for t in existing_tasks
                    if t.task_type == "scrape_stats" and t.tracker_url == tr
                ),
                None,
            )
            if not stat_task:
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
            elif stat_task.status in ("completed", "failed"):
                ref_ts = (
                    stat_task.tracker_updated_at
                    or stat_task.last_attempt_at
                    or stat_task.updated_at
                    or stat_task.created_at
                )
                should_renew = True
                if ref_ts:
                    try:
                        ref_dt = datetime.fromisoformat(ref_ts)
                        if (
                            (now - ref_dt).total_seconds()
                            < worker_settings.worker_scrape_stats_cooldown_seconds
                        ):
                            should_renew = False
                    except (ValueError, TypeError):
                        pass
                if should_renew:
                    self.task_repository.delete(stat_task.id)
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
            last_hit_at=resp_last_hit,
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
