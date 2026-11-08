import os
from typing import List
from pydantic_settings import BaseSettings

class AppSettings(BaseSettings):
    app_name: str = "torrent-stats API"
    debug: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


class CouchDBSettings(BaseSettings):
    couchdb_url: str = os.getenv("COUCHDB_URL", "http://admin:admin@localhost:5984")
    couchdb_db_name: str = os.getenv("COUCHDB_DB_NAME", "torrent_stats")

    class Config:
        env_file = ".env"
        extra = "ignore"


class RedisSettings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    class Config:
        env_file = ".env"
        extra = "ignore"


class WorkerSettings(BaseSettings):
    worker_failure_cooldown_seconds: int = int(os.getenv("WORKER_FAILURE_COOLDOWN_SECONDS", 12 * 3600))
    worker_stats_cooldown_seconds: int = int(os.getenv("WORKER_STATS_COOLDOWN_SECONDS", 6 * 3600))
    worker_task_lease_seconds: int = int(os.getenv("WORKER_TASK_LEASE_SECONDS", 300))

    class Config:
        env_file = ".env"
        extra = "ignore"


class TrackersSettings(BaseSettings):
    default_trackers: List[str] = (
        os.getenv("DEFAULT_TRACKERS", "").split(",")
        if os.getenv("DEFAULT_TRACKERS")
        else []
    )

    class Config:
        env_file = ".env"
        extra = "ignore"


app_settings = AppSettings()
couchdb_settings = CouchDBSettings()
redis_settings = RedisSettings()
worker_settings = WorkerSettings()
trackers_settings = TrackersSettings()
