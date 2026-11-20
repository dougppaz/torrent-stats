from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from torrent_stats.db.models import TaskDocument, TorrentMetadata
from torrent_stats.interfaces.api.depends import (
    get_hit_counter_service,
    get_storage_manager,
    get_task_repository,
    get_torrent_repository,
)
from torrent_stats.interfaces.api.main import app

client = TestClient(app)


def test_get_torrent_endpoint_missing():
    mock_repo = MagicMock = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = MagicMock()
    mock_hit_counter = MagicMock()
    mock_storage = MagicMock()

    mock_hit_counter.record_hit.return_value = (10, "2026-11-07T00:00:00Z")
    meta = TorrentMetadata(
        info_hash="abcdef123456", total_hits=10, last_hit_at="2026-11-07T00:00:00Z"
    )
    mock_repo.get_or_create.return_value = (meta, True)
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            info_hash="abcdef123456", task_type="scrape_torrent", status="pending"
        )
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get(
            "/torrents/abcdef123456?trackers=udp://tracker.opentrackr.org:1337"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["info_hash"] == "abcdef123456"
    assert data["total_hits"] == 10
    assert data["download_url"] is None
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "pending"


def test_get_torrent_endpoint_existing():
    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (5, "2026-11-07T00:00:00Z")
    meta = TorrentMetadata(
        info_hash="abcdef123456",
        name="Existing Torrent",
        total_size=1024,
        storage_profile_key="ftp",
        storage_params={"file_path": "torrents/abc.torrent"},
        total_hits=5,
        last_hit_at="2026-11-07T00:00:00Z",
    )
    mock_repo.get_or_create.return_value = (meta, False)
    mock_storage.get_download_url.return_value = (
        "https://download.asdf.com/torrents/abc.torrent"
    )
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            info_hash="abcdef123456", task_type="scrape_torrent", status="completed"
        )
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get("/torrents/abcdef123456")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Existing Torrent"
    assert data["download_url"] == "https://download.asdf.com/torrents/abc.torrent"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "completed"


@patch("torrent_stats.controllers.torrents.trackers_settings")
def test_get_torrent_with_default_trackers(mock_trackers_settings):
    mock_trackers_settings.default_trackers = ["udp://default.tracker:1337"]
    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (1, "2026-11-07T00:00:00Z")
    meta = TorrentMetadata(info_hash="abcdef123456", total_hits=1)
    mock_repo.get_or_create.return_value = (meta, True)
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            info_hash="abcdef123456", task_type="scrape_torrent", status="pending"
        )
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get("/torrents/abcdef123456")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data["tracker_stats"]) == 1
    assert data["tracker_stats"][0]["tracker_url"] == "udp://default.tracker:1337"


def test_get_torrent_task_error_message():
    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (1, "2026-11-07T00:00:00Z")
    meta = TorrentMetadata(info_hash="abcdef123456", total_hits=1)
    mock_repo.get_or_create.return_value = (meta, False)
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            info_hash="abcdef123456",
            task_type="scrape_torrent",
            status="failed",
            error_message="scrape_torrent task execution not yet implemented",
        )
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get("/torrents/abcdef123456")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "failed"
    assert (
        data["tasks"][0]["error_message"]
        == "scrape_torrent task execution not yet implemented"
    )
