from __future__ import annotations

from pydantic import BaseModel


class ActionSuccessResponse(BaseModel):
    status: str
    info_hash: str
