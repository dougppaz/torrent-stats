from __future__ import annotations

from torrent_stats.schemas.common import ActionSuccessResponse
from torrent_stats.schemas.task import (
    TaskClaimResponse,
    TaskFailureRequest,
    TaskResponse,
)
from torrent_stats.schemas.torrent import (
    TorrentDetailResponse,
    TorrentFileResponse,
)
from torrent_stats.schemas.tracker_stat import TrackerStatResponse

__all__ = [
    "ActionSuccessResponse",
    "TaskClaimResponse",
    "TaskFailureRequest",
    "TaskResponse",
    "TorrentDetailResponse",
    "TorrentFileResponse",
    "TrackerStatResponse",
]
