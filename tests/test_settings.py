import os
from unittest.mock import patch

from torrent_stats.settings import (
    AppSettings,
    CouchDBSettings,
    RedisSettings,
    StorageProfilesSettings,
    TrackersSettings,
    WorkerSettings,
)


def test_settings_initialization():
    app_s = AppSettings()
    assert app_s.app_name == "torrent-stats API"

    couch_s = CouchDBSettings()
    assert "localhost" in couch_s.couchdb_url

    redis_s = RedisSettings()
    assert "redis" in redis_s.redis_url

    worker_s = WorkerSettings()
    assert worker_s.worker_failure_cooldown_seconds == 43200

    trackers_s = TrackersSettings()
    assert isinstance(trackers_s.default_trackers, list)


@patch.dict(
    os.environ,
    {
        "STORAGE_PROFILE_FTP_TYPE": "ftp",
        "STORAGE_PROFILE_FTP_URL_TEMPLATE": "https://download.example.com/{file_path}",
        "STORAGE_PROFILE_FTP_HOST": "ftp.example.com",
        "CURRENT_STORAGE_PROFILE": "ftp",
    },
)
def test_storage_profiles_settings():
    # Force reload/reinstantiation of StorageProfilesSettings to read env vars
    storage_s = StorageProfilesSettings()
    assert storage_s.current_storage_profile == "ftp"
    assert "ftp" in storage_s.profiles
    assert storage_s.profiles["ftp"].type == "ftp"
    assert storage_s.profiles["ftp"].config["host"] == "ftp.example.com"
