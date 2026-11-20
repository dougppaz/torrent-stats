from __future__ import annotations

import logging
from datetime import UTC, datetime

from torrent_stats.db.models import TorrentMetadata, TrackerStat
from torrent_stats.db.repository import TaskRepository, TorrentMetadataRepository
from torrent_stats.schemas import ActionSuccessResponse

logger = logging.getLogger("torrent_stats.worker")


class TrackerStatsController:
    def __init__(
        self,
        torrent_repository: TorrentMetadataRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.torrent_repo = torrent_repository
        self.task_repo = task_repository

    def submit_stats(
        self,
        hash: str,
        tracker_url: str,
        success: bool,
        seeds: int | None = 0,
        peers: int | None = 0,
    ) -> ActionSuccessResponse:
        torrent = self.torrent_repo.find_by_info_hash(hash)
        if not torrent:
            torrent = TorrentMetadata(info_hash=hash)

        now = datetime.now(UTC).isoformat()

        existing_stat = None
        for stat in torrent.tracker_stats:
            if stat.tracker_url == tracker_url:
                existing_stat = stat
                break

        if existing_stat:
            if success:
                existing_stat.seeds = seeds or 0
                existing_stat.peers = peers or 0
                existing_stat.updated_at = now
                existing_stat.consecutive_failures = 0
            else:
                existing_stat.consecutive_failures += 1
        else:
            if success:
                torrent.tracker_stats.append(
                    TrackerStat(
                        tracker_url=tracker_url,
                        seeds=seeds or 0,
                        peers=peers or 0,
                        updated_at=now,
                        consecutive_failures=0,
                    )
                )
            else:
                torrent.tracker_stats.append(
                    TrackerStat(
                        tracker_url=tracker_url,
                        seeds=0,
                        peers=0,
                        updated_at=now,
                        consecutive_failures=1,
                    )
                )

        torrent.tracker_stats = [
            s for s in torrent.tracker_stats if s.consecutive_failures < 3
        ]

        self.torrent_repo.save(torrent)

        tasks = self.task_repo.find_by_info_hash(hash)
        stat_task = next(
            (
                t
                for t in tasks
                if t.task_type == "scrape_stats" and t.tracker_url == tracker_url
            ),
            None,
        )
        if stat_task:
            stat_task.status = "completed" if success else "failed"
            stat_task.last_attempt_at = now
            if success:
                stat_task.tracker_updated_at = now
            self.task_repo.save(stat_task)

        return ActionSuccessResponse(status="success", info_hash=hash)
