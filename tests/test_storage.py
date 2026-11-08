from unittest.mock import patch

import pytest
from torrent_stats.services.storage import StorageManager
from torrent_stats.settings import StorageProfileConfig


@patch("torrent_stats.services.storage.storage_profiles_settings")
def test_storage_manager_memory(mock_storage_settings):
    mock_storage_settings.current_storage_profile = "mem"
    mock_storage_settings.profiles = {
        "mem": StorageProfileConfig(
            type="memory",
            config={"url_template": "https://download.test.com/{file_path}"},
        )
    }

    manager = StorageManager()
    profile_key, storage_params, download_url = manager.upload_torrent(
        "abc123hash", b"torrent-file-content"
    )

    assert profile_key == "mem"
    assert storage_params == {"file_path": "torrents/abc123hash.torrent"}
    assert download_url == "https://download.test.com/torrents/abc123hash.torrent"

    # Test get_download_url
    url = manager.get_download_url(profile_key, storage_params)
    assert url == download_url

    # Test get_download_url with missing profile or params
    assert manager.get_download_url("unknown", storage_params) is None
    assert manager.get_download_url(profile_key, None) is None
    assert manager.get_download_url(profile_key, {"wrong_key": "val"}) is None


@patch("torrent_stats.services.storage.storage_profiles_settings")
def test_storage_manager_fallback(mock_storage_settings):
    mock_storage_settings.current_storage_profile = "nonexistent"
    mock_storage_settings.profiles = {
        "fallback": StorageProfileConfig(
            type="memory",
            config={},
        )
    }

    manager = StorageManager()
    profile_key, _, _ = manager.upload_torrent(
        "hash", b"content", explicit_profile_key="fallback"
    )
    assert profile_key == "fallback"


@patch("torrent_stats.services.storage.storage_profiles_settings")
def test_storage_manager_no_profiles(mock_storage_settings):
    mock_storage_settings.current_storage_profile = "missing"
    mock_storage_settings.profiles = {}

    manager = StorageManager()
    with pytest.raises(ValueError, match="No storage profiles configured"):
        manager.upload_torrent("hash", b"content")
