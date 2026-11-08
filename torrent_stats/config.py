import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "torrent-stats API"
    couchdb_url: str = os.getenv("COUCHDB_URL", "http://admin:admin@localhost:5984")
    couchdb_db_name: str = os.getenv("COUCHDB_DB_NAME", "torrent_stats")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Cooldowns (in seconds)
    worker_failure_cooldown_seconds: int = int(os.getenv("WORKER_FAILURE_COOLDOWN_SECONDS", 12 * 3600))
    worker_stats_cooldown_seconds: int = int(os.getenv("WORKER_STATS_COOLDOWN_SECONDS", 6 * 3600))
    worker_task_lease_seconds: int = int(os.getenv("WORKER_TASK_LEASE_SECONDS", 300))
    
    # Default trackers if infohash provided without magnet
    default_trackers: list = os.getenv("DEFAULT_TRACKERS", "").split(",") if os.getenv("DEFAULT_TRACKERS") else []

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
