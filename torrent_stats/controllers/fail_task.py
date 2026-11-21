from __future__ import annotations

import logging
from datetime import UTC, datetime

from torrent_stats.db.repository import TaskRepository
from torrent_stats.schemas import ActionSuccessResponse

logger = logging.getLogger("torrent_stats.worker")


class TaskFailureController:
    def __init__(self, task_repository: TaskRepository) -> None:
        self.task_repo = task_repository

    def fail_task(
        self, task_id: str, error_message: str
    ) -> ActionSuccessResponse | None:
        task = self.task_repo.get(task_id)
        if not task:
            return None

        updated = self.task_repo.update_task_status(
            task_id=task_id,
            status="failed",
            error_message=error_message,
            last_attempt_at=datetime.now(UTC).isoformat(),
        )
        if not updated:
            return None
        task = updated

        logger.warning("Task %s failed: %s", task_id, error_message)
        return ActionSuccessResponse(status="success", info_hash=task.info_hash)
