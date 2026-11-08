from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class TorrentFile(BaseModel):
    path: list[str]
    length: int


class TorrentMetadata(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    infoHash: str
    name: str = ""
    totalSize: int = 0
    torrentStorageRef: str = ""
    storageProfileId: str = ""
    filePath: str = ""
    totalHits: int = 0
    lastHitAt: str | None = None
    files: list[TorrentFile] = []
    createdAt: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        populate_by_name = True


class StorageProfile(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    type: str = "ftp"
    config: dict[str, Any] = {}
    urlTemplate: str = "https://download.asdf.com/{file_path}"

    class Config:
        populate_by_name = True


class WorkerKey(BaseModel):
    id: str = Field(alias="_id", default="")
    rev: str | None = Field(alias="_rev", default=None)
    keyHash: str
    description: str = ""
    createdAt: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    class Config:
        populate_by_name = True
