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
    assert worker_s.worker_scrape_stats_failure_cooldown_seconds == 10800
    assert worker_s.worker_scrape_torrent_failure_cooldown_seconds == 3600
    assert worker_s.worker_scrape_stats_cooldown_seconds == 1800

    trackers_s = TrackersSettings()
    assert isinstance(trackers_s.default_trackers, list)


@patch.dict(
    os.environ,
    {"DEFAULT_TRACKERS": "udp://tracker1.com:1337, udp://tracker2.com:1337"},
)
def test_trackers_settings_comma_separated():
    ts = TrackersSettings()
    assert ts.default_trackers == [
        "udp://tracker1.com:1337",
        "udp://tracker2.com:1337",
    ]


@patch.dict(
    os.environ,
    {"DEFAULT_TRACKERS": '["udp://json1.com:1337", "udp://json2.com:1337"]'},
)
def test_trackers_settings_json():
    ts = TrackersSettings()
    assert ts.default_trackers == ["udp://json1.com:1337", "udp://json2.com:1337"]


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
