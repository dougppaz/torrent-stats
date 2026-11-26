from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TorrentFile(BaseModel):
    path: str
    length: int


class TrackerStat(BaseModel):
    tracker_url: str
    seeds: int | None = None
    peers: int | None = None
    updated_at: datetime | None = None
    consecutive_failures: int = 0


class TaskItem(BaseModel):
    task_id: str
    task_type: str = "scrape_torrent"  # scrape_torrent, scrape_stats
    status: str = "pending"  # pending, claimed, scraping, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    claimed_at: datetime | None = None
    lease_expires_at: datetime | None = None
    last_attempt_at: datetime | None = None
    updated_at: datetime | None = None
    error_message: str | None = None


class TaskDocument(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    info_hash: str
    task_type: str = "scrape_torrent"  # scrape_torrent, scrape_stats
    status: str = "pending"  # pending, claimed, scraping, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    claimed_at: datetime | None = None
    lease_expires_at: datetime | None = None
    last_attempt_at: datetime | None = None
    updated_at: datetime | None = None
    error_message: str | None = None
    tracker_url: str | None = None
    tracker_updated_at: datetime | None = None

    @model_validator(mode="after")
    def set_id(self) -> TaskDocument:
        if not self.id:
            from uuid import uuid4

            suffix = f"-{abs(hash(self.tracker_url))}" if self.tracker_url else ""
            self.id = (
                f"task-{self.info_hash}-{self.task_type}{suffix}-{uuid4().hex[:8]}"
            )
        return self

    model_config = {"populate_by_name": True, "extra": "ignore"}


class TrackerStatDocument(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    info_hash: str
    tracker_url: str
    seeds: int | None = None
    peers: int | None = None
    updated_at: datetime | None = None
    consecutive_failures: int = 0

    @model_validator(mode="after")
    def set_id(self) -> TrackerStatDocument:
        if not self.id:
            self.id = f"tracker-{self.info_hash}-{abs(hash(self.tracker_url))}"
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
    files: list[TorrentFile] | None = None
    tasks: list[TaskItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def set_id(self) -> WorkerKey:
        if not self.id and self.key_hash:
            self.id = self.key_hash
        return self

    model_config = {"populate_by_name": True, "extra": "ignore"}
