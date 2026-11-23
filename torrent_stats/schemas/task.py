from __future__ import annotations

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    tracker_url: str | None = None
    updated_at: str | None = None
    created_at: str | None = None
    error_message: str | None = None


class TaskClaimResponse(BaseModel):
    task_id: str
    info_hash: str
    task_type: str
    tracker_url: str | None = None
    updated_at: str | None = None
    lease_expires_at: str
    trackers: list[str] = Field(default_factory=list)


class TaskFailureRequest(BaseModel):
    error_message: str
