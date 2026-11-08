from __future__ import annotations

import os
from typing import Any

import fsspec
from torrent_stats.services.storage.base import BaseStorage
from torrent_stats.settings import StorageProfileConfig


class LocalStorage(BaseStorage):
    def __init__(self, profile: StorageProfileConfig) -> None:
        super().__init__(profile)
        fs_config = profile.config.copy()
        fs_config.pop("download_url_template", None)
        fs_config.pop("target_path_template", None)
        self.fs = fsspec.filesystem("file", **fs_config)

    def upload(self, info_hash: str, file_bytes: bytes) -> dict[str, Any]:
        template = self.profile.config.get(
            "target_path_template", ".torrents/{info_hash}.torrent"
        )
        target_path = str(template).format(info_hash=info_hash)

        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            self.fs.makedirs(parent_dir, exist_ok=True)

        with self.fs.open(target_path, "wb") as f:
            f.write(file_bytes)
        return {"target_path": target_path}

    def get_download_url(self, storage_params: dict[str, Any]) -> str:
        target_path = storage_params.get("target_path")
        if not target_path:
            raise ValueError("Storage params are missing 'target_path'.")
        url_template = self.profile.config.get("download_url_template")
        if url_template:
            return str(url_template).format(**storage_params)
        return os.path.abspath(str(target_path))
