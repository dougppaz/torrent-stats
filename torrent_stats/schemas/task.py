from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    tracker_url: str | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None
    error_message: str | None = None


class TaskClaimResponse(BaseModel):
    task_id: str
    info_hash: str
    task_type: str
    tracker_url: str | None = None
    updated_at: datetime | None = None
    lease_expires_at: datetime | None = None
    trackers: list[str] = Field(default_factory=list)


class TaskFailureRequest(BaseModel):
    error_message: str
