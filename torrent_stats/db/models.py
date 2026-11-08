from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TorrentFile(BaseModel):
    path: list[str]
    length: int


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
