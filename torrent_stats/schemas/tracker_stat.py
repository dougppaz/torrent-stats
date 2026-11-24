from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TrackerStatResponse(BaseModel):
    tracker_url: str
    seeds: int | None = None
    peers: int | None = None
    updated_at: datetime | None = None
