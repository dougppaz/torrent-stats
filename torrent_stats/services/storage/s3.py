from __future__ import annotations

from typing import Any

import fsspec
from torrent_stats.services.storage.base import BaseStorage
from torrent_stats.settings import StorageProfileConfig


class S3Storage(BaseStorage):
    def __init__(self, profile: StorageProfileConfig) -> None:
        super().__init__(profile)
        fs_config = profile.config.copy()
        fs_config.pop("download_url_template", None)
        fs_config.pop("target_path_template", None)
        fs_config.pop("bucket", None)

        region_name = fs_config.pop("region_name", None)
        if region_name:
            client_kwargs = fs_config.get("client_kwargs", {})
            if isinstance(client_kwargs, dict):
                client_kwargs.setdefault("region_name", region_name)
            else:
                client_kwargs = {"region_name": region_name}
            fs_config["client_kwargs"] = client_kwargs

        self.fs = fsspec.filesystem("s3", **fs_config)

    def upload(self, info_hash: str, file_bytes: bytes) -> dict[str, Any]:
        bucket = self.profile.config.get("bucket")
        template = self.profile.config.get(
            "target_path_template", "torrents/{info_hash}.torrent"
        )
        target_path = str(template).format(info_hash=info_hash, **self.profile.config)

        if bucket and target_path.startswith(f"{bucket}/"):
            target_path = target_path[len(bucket) + 1 :]

        full_path = f"{bucket}/{target_path}" if bucket else target_path

        with self.fs.open(full_path, "wb") as f:
            f.write(file_bytes)
        return {
            "bucket": bucket,
            "target_path": target_path,
            "full_path": full_path,
        }

    def get_download_url(self, storage_params: dict[str, Any]) -> str:
        target_path = storage_params.get("target_path")
        if not target_path:
            raise ValueError("Storage params are missing 'target_path'.")
        url_template = self.profile.config.get("download_url_template")
        if not url_template:
            raise ValueError(
                f"Storage profile '{self.profile.type}' is missing 'download_url_template' in config."
            )
        params = {**self.profile.config, **storage_params}
        url: str = str(url_template).format(**params)
        return url
