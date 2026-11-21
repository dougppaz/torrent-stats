from __future__ import annotations

import logging
from datetime import UTC, datetime

from torrent_stats.db.models import TaskDocument
from torrent_stats.db.repository import TaskRepository
from torrent_stats.schemas import TaskClaimResponse
from torrent_stats.settings import WorkerSettings

logger = logging.getLogger("torrent_stats.worker")


class TaskClaimController:
    def __init__(
        self,
        task_repository: TaskRepository,
        worker_settings: WorkerSettings,
    ) -> None:
        self.task_repo = task_repository
        self.worker_settings = worker_settings

    def claim_task(self) -> TaskClaimResponse | None:
        now = datetime.now(UTC)
        all_tasks = self.task_repo.find_claimable()
        logger.debug(
            "Evaluating task claim. Total tasks in repository: %d", len(all_tasks)
        )

        candidates: list[TaskDocument] = []
        for task in all_tasks:
            # Check failure cooldown (12h)
            if task.last_attempt_at and task.status == "failed":
                last_attempt = datetime.fromisoformat(task.last_attempt_at)
                if (
                    (now - last_attempt).total_seconds()
                    < self.worker_settings.worker_failure_cooldown_seconds
                ):
                    logger.debug(
                        "Task %s skipped: failure cooldown active (last attempt at %s).",
                        task.id,
                        task.last_attempt_at,
                    )
                    continue

            # Check stats update cooldown (6h) for scrape_stats tasks using denormalized tracker_updated_at
            if (
                task.task_type == "scrape_stats"
                and task.tracker_url
                and task.tracker_updated_at is not None
            ):
                tracker_updated = datetime.fromisoformat(task.tracker_updated_at)
                if (
                    now - tracker_updated
                ).total_seconds() < self.worker_settings.worker_stats_cooldown_seconds:
                    logger.debug(
                        "Task %s skipped: stats update cooldown active for tracker %s.",
                        task.id,
                        task.tracker_url,
                    )
                    continue

            logger.debug(
                "Task %s (type: %s) added as claim candidate.", task.id, task.task_type
            )
            candidates.append(task)

        if not candidates:
            logger.info("No claimable tasks available.")
            return None

        # Prioritize scrape_torrent over scrape_stats, then by creation date
        candidates.sort(
            key=lambda x: (0 if x.task_type == "scrape_torrent" else 1, x.created_at)
        )

        task = candidates[0]
        logger.debug(
            "Selected top candidate task %s (type: %s) out of %d candidates.",
            task.id,
            task.task_type,
            len(candidates),
        )

        lease_expires = now.timestamp() + self.worker_settings.worker_task_lease_seconds
        lease_expires_at = datetime.fromtimestamp(lease_expires, UTC).isoformat()
        updated = self.task_repo.update_task_status(
            task_id=task.id,
            status="claimed",
            lease_expires_at=lease_expires_at,
            claimed_at=now.isoformat(),
            last_attempt_at=now.isoformat(),
        )
        if updated:
            task = updated

        logger.info(
            "Worker successfully claimed task %s for info_hash %s (type: %s, lease expires at %s).",
            task.id,
            task.info_hash,
            task.task_type,
            task.lease_expires_at,
        )

        return TaskClaimResponse(
            task_id=task.id,
            info_hash=task.info_hash,
            task_type=task.task_type,
            tracker_url=task.tracker_url,
            updated_at=task.tracker_updated_at,
            lease_expires_at=task.lease_expires_at or "",
        )
