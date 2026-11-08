from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    app_name: str = "torrent-stats API"
    debug: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


class CouchDBSettings(BaseSettings):
    couchdb_url: str = "http://admin:admin@localhost:5984/"
    couchdb_db_name: str = "torrent_stats"

    class Config:
        env_file = ".env"
        extra = "ignore"


class RedisSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        extra = "ignore"


class WorkerSettings(BaseSettings):
    worker_failure_cooldown_seconds: int = 12 * 3600
    worker_stats_cooldown_seconds: int = 6 * 3600
    worker_task_lease_seconds: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"


class TrackersSettings(BaseSettings):
    default_trackers: list[str] = []

    class Config:
        env_file = ".env"
        extra = "ignore"


class StorageProfileConfig(BaseModel):
    type: str = "ftp"
    url_template: str = "https://download.asdf.com/{file_path}"
    config: dict[str, Any] = {}


class StorageProfilesSettings(BaseSettings):
    profiles: dict[str, StorageProfileConfig] = {}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        profiles_dict: dict[str, dict[str, Any]] = {}
        for key, value in os.environ.items():
            if key.startswith("STORAGE_PROFILE_"):
                parts = key[len("STORAGE_PROFILE_") :].lower().split("_", 1)
                if len(parts) == 2:
                    profile_key, param = parts
                    if profile_key not in profiles_dict:
                        profiles_dict[profile_key] = {
                            "config": {},
                            "type": "ftp",
                            "url_template": "https://download.asdf.com/{file_path}",
                        }

                    if param == "type":
                        profiles_dict[profile_key]["type"] = value
                    elif param == "url_template":
                        profiles_dict[profile_key]["url_template"] = value
                    else:
                        profiles_dict[profile_key]["config"][param] = value

        if not profiles_dict:
            # Default fallback profile
            profiles_dict["default"] = {
                "type": "ftp",
                "url_template": "https://download.asdf.com/{file_path}",
                "config": {},
            }

        self.profiles = {k: StorageProfileConfig(**v) for k, v in profiles_dict.items()}

    class Config:
        env_file = ".env"
        extra = "ignore"


app_settings = AppSettings()
couchdb_settings = CouchDBSettings()
redis_settings = RedisSettings()
worker_settings = WorkerSettings()
trackers_settings = TrackersSettings()
storage_profiles_settings = StorageProfilesSettings()
