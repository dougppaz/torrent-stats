from __future__ import annotations

import logging
from datetime import UTC, datetime

from torrent_stats.db.repository import TaskRepository
from torrent_stats.interfaces.api.schemas import ActionSuccessResponse

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

        task.status = "failed"
        task.error_message = error_message
        task.last_attempt_at = datetime.now(UTC).isoformat()
        self.task_repo.save(task)

        logger.warning("Task %s failed: %s", task_id, error_message)
        return ActionSuccessResponse(status="success", info_hash=task.info_hash)
