from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from torrent_stats.schemas.task import TaskResponse
from torrent_stats.schemas.tracker_stat import TrackerStatResponse


class TorrentFileResponse(BaseModel):
    path: str
    length: int


class TorrentDetailResponse(BaseModel):
    info_hash: str
    name: str | None = None
    total_size: int | None = None
    storage_profile_key: str | None = None
    storage_params: dict[str, Any] | None = None
    download_url: str | None = None
    total_hits: int = 0
    last_hit_at: datetime | None = None
    files: list[TorrentFileResponse] | None = None
    tracker_stats: list[TrackerStatResponse] = []
    tasks: list[TaskResponse] = []
