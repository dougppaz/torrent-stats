from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class TorrentFileResponse(BaseModel):
    path: list[str]
    length: int


class TrackerStatResponse(BaseModel):
    tracker_url: str
    seeds: int | None = None
    peers: int | None = None
    updated_at: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    tracker_url: str | None = None
    updated_at: str | None = None
    created_at: str | None = None
    error_message: str | None = None


class TorrentDetailResponse(BaseModel):
    info_hash: str
    name: str | None = None
    total_size: int | None = None
    storage_profile_key: str | None = None
    storage_params: dict[str, Any] | None = None
    download_url: str | None = None
    total_hits: int = 0
    last_hit_at: str | None = None
    files: list[TorrentFileResponse] | None = None
    tracker_stats: list[TrackerStatResponse] = []
    tasks: list[TaskResponse] = []


class TaskClaimResponse(BaseModel):
    task_id: str
    info_hash: str
    task_type: str
    tracker_url: str | None = None
    updated_at: str | None = None
    lease_expires_at: str


class TaskFailureRequest(BaseModel):
    error_message: str


class ActionSuccessResponse(BaseModel):
    status: str
    info_hash: str
