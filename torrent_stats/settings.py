from __future__ import annotations

from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    app_name: str = "torrent-stats API"
    debug: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


class CouchDBSettings(BaseSettings):
    couchdb_url: str = "http://admin:admin@localhost:5984"
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


app_settings = AppSettings()
couchdb_settings = CouchDBSettings()
redis_settings = RedisSettings()
worker_settings = WorkerSettings()
trackers_settings = TrackersSettings()
