from __future__ import annotations

from typing import Any

import fsspec
from torrent_stats.services.storage.base import BaseStorage
from torrent_stats.settings import StorageProfileConfig


class FTPStorage(BaseStorage):
    def __init__(self, profile: StorageProfileConfig) -> None:
        super().__init__(profile)
        fs_config = profile.config.copy()
        fs_config.pop("download_url_template", None)
        fs_config.pop("target_path_template", None)
        self.fs = fsspec.filesystem("ftp", **fs_config)

    def upload(self, info_hash: str, file_bytes: bytes) -> dict[str, Any]:
        template = self.profile.config.get(
            "target_path_template", ".torrents/{info_hash}.torrent"
        )
        target_path = str(template).format(info_hash=info_hash)
        with self.fs.open(target_path, "wb") as f:
            f.write(file_bytes)
        return {"target_path": target_path}

    def get_download_url(self, storage_params: dict[str, Any]) -> str:
        url_template = self.profile.config.get("download_url_template")
        if not url_template:
            raise ValueError(
                f"Storage profile '{self.profile.type}' is missing 'download_url_template' in config."
            )
        url: str = str(url_template).format(**storage_params)
        return url
