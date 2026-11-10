from __future__ import annotations

from torrent_stats.controllers.claim_task import TaskClaimController
from torrent_stats.controllers.submit_tracker_stats import TrackerStatsController
from torrent_stats.controllers.torrents import TorrentController
from torrent_stats.controllers.upload_torrent import TorrentUploadController

__all__ = [
    "TaskClaimController",
    "TorrentController",
    "TorrentUploadController",
    "TrackerStatsController",
]
