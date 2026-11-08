from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from torrent_stats.settings import StorageProfileConfig


class BaseStorage(ABC):
    def __init__(self, profile: StorageProfileConfig) -> None:
        self.profile = profile

    @abstractmethod
    def upload(self, info_hash: str, file_bytes: bytes) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_download_url(self, storage_params: dict[str, Any]) -> str:
        pass
