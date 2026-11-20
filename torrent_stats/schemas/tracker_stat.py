from __future__ import annotations

from pydantic import BaseModel


class TrackerStatResponse(BaseModel):
    tracker_url: str
    seeds: int | None = None
    peers: int | None = None
    updated_at: str | None = None
