from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class TorrentFile(BaseModel):
    path: list[str]
    length: int


class TorrentMetadata(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    info_hash: str
    name: str = ""
    total_size: int = 0
    torrent_storage_ref: str = ""
    storage_profile_id: str = ""
    file_path: str = ""
    total_hits: int = 0
    last_hit_at: str | None = None
    files: list[TorrentFile] = []
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        populate_by_name = True


class WorkerKey(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    key_hash: str
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        populate_by_name = True
