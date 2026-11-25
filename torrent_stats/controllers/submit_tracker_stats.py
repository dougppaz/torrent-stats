from __future__ import annotations

import logging
from datetime import UTC, datetime

from torrent_stats.db.repository import TaskRepository, TrackerStatsRepository
from torrent_stats.schemas import ActionSuccessResponse

logger = logging.getLogger("torrent_stats.worker")


class TrackerStatsController:
    def __init__(
        self,
        tracker_stats_repository: TrackerStatsRepository,
        task_repository: TaskRepository,
    ) -> None:
        self.tracker_stats_repo = tracker_stats_repository
        self.task_repo = task_repository

    def submit_stats(
        self,
        hash: str,
        tracker_url: str,
        success: bool,
        seeds: int | None = 0,
        peers: int | None = 0,
    ) -> ActionSuccessResponse:
        now = datetime.now(UTC)

        if success:
            self.tracker_stats_repo.update_stats(
                hash, tracker_url, seeds or 0, peers or 0
            )
        else:
            doc = self.tracker_stats_repo.increment_failure(hash, tracker_url)
            if doc.consecutive_failures >= 3:
                self.tracker_stats_repo.delete(doc.id)

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
            stat_task.updated_at = now
            if success:
                stat_task.tracker_updated_at = now
            self.task_repo.save(stat_task)

        return ActionSuccessResponse(status="success", info_hash=hash)
