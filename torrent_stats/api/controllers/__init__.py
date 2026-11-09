from __future__ import annotations

from torrent_stats.api.controllers.torrents import TorrentController
from torrent_stats.api.controllers.worker import (
    TaskClaimController,
    TorrentUploadController,
    TrackerStatsController,
)

__all__ = [
    "TaskClaimController",
    "TorrentController",
    "TorrentUploadController",
    "TrackerStatsController",
]
