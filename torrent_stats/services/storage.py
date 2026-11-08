from __future__ import annotations

from typing import Any

import fsspec
from torrent_stats.settings import StorageProfileConfig, storage_profiles_settings


class StorageManager:
    def get_active_profile(self) -> tuple[str, StorageProfileConfig]:
        profile_key = storage_profiles_settings.current_storage_profile
        profile = storage_profiles_settings.profiles.get(profile_key)
        if not profile:
            if storage_profiles_settings.profiles:
                profile_key, profile = next(
                    iter(storage_profiles_settings.profiles.items())
                )
            else:
                raise ValueError("No storage profiles configured.")
        return profile_key, profile

    def upload_torrent(
        self,
        info_hash: str,
        file_bytes: bytes,
        explicit_profile_key: str | None = None,
    ) -> tuple[str, dict[str, Any], str]:
        if (
            explicit_profile_key
            and explicit_profile_key in storage_profiles_settings.profiles
        ):
            profile_key = explicit_profile_key
            profile = storage_profiles_settings.profiles[profile_key]
        else:
            profile_key, profile = self.get_active_profile()

        file_path = f"torrents/{info_hash}.torrent"
        storage_params = {"file_path": file_path}

        fs_type = profile.type
        fs_config = profile.config.copy()
        fs_config.pop("url_template", None)

        fs = fsspec.filesystem(fs_type, **fs_config)
        with fs.open(file_path, "wb") as f:
            f.write(file_bytes)

        url_template = profile.config.get(
            "url_template", "https://download.asdf.com/{file_path}"
        )
        download_url = str(url_template).format(**storage_params)

        return profile_key, storage_params, download_url

    def get_download_url(
        self, profile_key: str | None, storage_params: dict[str, Any] | None
    ) -> str | None:
        if not profile_key or not storage_params:
            return None
        profile = storage_profiles_settings.profiles.get(profile_key)
        if not profile:
            return None
        url_template = profile.config.get(
            "url_template", "https://download.asdf.com/{file_path}"
        )
        try:
            url: str = str(url_template).format(**storage_params)
            return url
        except KeyError:
            return None


storage_manager = StorageManager()
