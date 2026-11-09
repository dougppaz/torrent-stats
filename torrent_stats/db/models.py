from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TorrentFile(BaseModel):
    path: list[str]
    length: int


class TrackerStat(BaseModel):
    tracker_url: str
    seeds: int = 0
    peers: int = 0
    updated_at: str = "1970-01-01T00:00:00Z"
    consecutive_failures: int = 0


class TaskItem(BaseModel):
    task_id: str
    task_type: str = "scrape_torrent"  # scrape_torrent, scrape_stats
    status: str = "pending"  # pending, claimed, scraping, completed, failed
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    claimed_at: str | None = None
    lease_expires_at: str | None = None
    last_attempt_at: str | None = None
    error_message: str | None = None


class TaskDocument(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    info_hash: str
    task_type: str = "scrape_torrent"  # scrape_torrent, scrape_stats
    status: str = "pending"  # pending, claimed, scraping, completed, failed
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    claimed_at: str | None = None
    lease_expires_at: str | None = None
    last_attempt_at: str | None = None
    error_message: str | None = None
    tracker_url: str | None = None

    @model_validator(mode="after")
    def set_id(self) -> TaskDocument:
        if not self.id:
            suffix = f"-{abs(hash(self.tracker_url))}" if self.tracker_url else ""
            self.id = f"task-{self.info_hash}-{self.task_type}{suffix}"
        return self

    model_config = {"populate_by_name": True, "extra": "ignore"}


class TorrentMetadata(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    info_hash: str
    name: str | None = None
    total_size: int | None = None
    storage_profile_key: str | None = None
    storage_params: dict[str, Any] | None = None
    total_hits: int = 0
    last_hit_at: str | None = None
    files: list[TorrentFile] | None = None
    tracker_stats: list[TrackerStat] = Field(default_factory=list)
    tasks: list[TaskItem] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="after")
    def set_id(self) -> TorrentMetadata:
        if not self.id and self.info_hash:
            self.id = self.info_hash
        return self

    model_config = {"populate_by_name": True, "extra": "ignore"}


class WorkerKey(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    key_hash: str
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="after")
    def set_id(self) -> WorkerKey:
        if not self.id and self.key_hash:
            self.id = self.key_hash
        return self

    model_config = {"populate_by_name": True, "extra": "ignore"}
