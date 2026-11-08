import os
from unittest.mock import patch

import pytest
from torrent_stats.services.storage.manager import StorageManager
from torrent_stats.settings import StorageProfileConfig


@patch("torrent_stats.services.storage.manager.storage_profiles_settings")
def test_storage_manager_local(mock_storage_settings, tmp_path):
    target_template = str(tmp_path / ".torrents" / "{info_hash}.torrent")

    mock_storage_settings.current_storage_profile = "local_profile"
    mock_storage_settings.profiles = {
        "local_profile": StorageProfileConfig(
            type="local",
            config={
                "target_path_template": target_template,
            },
        )
    }

    manager = StorageManager()
    profile_key, storage_params, download_url = manager.upload_torrent(
        "abc123hash", b"torrent-file-content"
    )

    assert profile_key == "local_profile"
    expected_path = str(tmp_path / ".torrents" / "abc123hash.torrent")
    assert storage_params == {
        "target_path": expected_path,
    }
    assert download_url == expected_path

    # Check file exists in temp directory
    assert os.path.exists(expected_path)

    # Test get_download_url
    url = manager.get_download_url(profile_key, storage_params)
    assert url == expected_path

    # Test get_download_url with missing profile or params
    assert manager.get_download_url("unknown", storage_params) is None
    assert manager.get_download_url(profile_key, None) is None
    assert manager.get_download_url(profile_key, {"wrong_key": "val"}) is None


@patch("torrent_stats.services.storage.manager.storage_profiles_settings")
def test_storage_manager_fallback(mock_storage_settings, tmp_path):
    target_template = str(tmp_path / "fallback.torrent")
    mock_storage_settings.current_storage_profile = "nonexistent"
    mock_storage_settings.profiles = {
        "fallback": StorageProfileConfig(
            type="local",
            config={
                "target_path_template": target_template,
            },
        )
    }

    manager = StorageManager()
    profile_key, _, _ = manager.upload_torrent(
        "hash", b"content", explicit_profile_key="fallback"
    )
    assert profile_key == "fallback"


@patch("torrent_stats.services.storage.manager.storage_profiles_settings")
def test_storage_manager_no_profiles(mock_storage_settings):
    mock_storage_settings.current_storage_profile = "missing"
    mock_storage_settings.profiles = {}

    manager = StorageManager()
    with pytest.raises(ValueError, match="No storage profiles configured"):
        manager.upload_torrent("hash", b"content")


@patch("torrent_stats.services.storage.manager.storage_profiles_settings")
def test_storage_manager_unsupported_type(mock_storage_settings):
    mock_storage_settings.current_storage_profile = "unsupported"
    mock_storage_settings.profiles = {
        "unsupported": StorageProfileConfig(
            type="unknown_storage_type",
            config={},
        )
    }
    manager = StorageManager()
    with pytest.raises(ValueError, match="Unsupported storage profile type"):
        manager.upload_torrent("hash", b"content")
