from __future__ import annotations

from typing import Any

from torrent_stats.services.storage.base import BaseStorage
from torrent_stats.services.storage.ftp import FTPStorage
from torrent_stats.services.storage.local import LocalStorage
from torrent_stats.settings import StorageProfileConfig, storage_profiles_settings

STORAGE_REGISTRY: dict[str, type[BaseStorage]] = {
    "ftp": FTPStorage,
    "local": LocalStorage,
    "file": LocalStorage,
}


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

    def get_storage_handler(
        self, profile_key: str | None = None
    ) -> tuple[str, BaseStorage]:
        if profile_key and profile_key in storage_profiles_settings.profiles:
            pk = profile_key
            profile = storage_profiles_settings.profiles[pk]
        else:
            pk, profile = self.get_active_profile()

        storage_class = STORAGE_REGISTRY.get(profile.type)
        if not storage_class:
            raise ValueError(f"Unsupported storage profile type: '{profile.type}'")

        return pk, storage_class(profile)

    def upload_torrent(
        self,
        info_hash: str,
        file_bytes: bytes,
        explicit_profile_key: str | None = None,
    ) -> tuple[str, dict[str, Any], str]:
        profile_key, handler = self.get_storage_handler(explicit_profile_key)

        storage_params = handler.upload(info_hash, file_bytes)
        download_url = handler.get_download_url(storage_params)

        return profile_key, storage_params, download_url

    def get_download_url(
        self, profile_key: str | None, storage_params: dict[str, Any] | None
    ) -> str | None:
        if not profile_key or not storage_params:
            return None
        profile = storage_profiles_settings.profiles.get(profile_key)
        if not profile:
            return None
        storage_class = STORAGE_REGISTRY.get(profile.type)
        if not storage_class:
            return None
        handler = storage_class(profile)
        try:
            return handler.get_download_url(storage_params)
        except (ValueError, KeyError):
            return None


storage_manager = StorageManager()
