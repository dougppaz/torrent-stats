from unittest.mock import patch

from fastapi.testclient import TestClient
from torrent_stats.db.models import TaskDocument, TorrentMetadata
from torrent_stats.main import app

client = TestClient(app)


@patch("torrent_stats.api.routers.torrents.task_repo")
@patch("torrent_stats.api.routers.torrents.storage_manager")
@patch("torrent_stats.api.routers.torrents.torrent_repo")
@patch("torrent_stats.api.routers.torrents.hit_counter_service")
def test_get_torrent_endpoint_missing(
    mock_hit_counter, mock_repo, mock_storage, mock_task_repo
):
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

    response = client.get(
        "/torrents/abcdef123456?trackers=udp://tracker.opentrackr.org:1337"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["info_hash"] == "abcdef123456"
    assert data["total_hits"] == 10
    assert data["download_url"] is None
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "pending"


@patch("torrent_stats.api.routers.torrents.task_repo")
@patch("torrent_stats.api.routers.torrents.storage_manager")
@patch("torrent_stats.api.routers.torrents.torrent_repo")
@patch("torrent_stats.api.routers.torrents.hit_counter_service")
def test_get_torrent_endpoint_existing(
    mock_hit_counter, mock_repo, mock_storage, mock_task_repo
):
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

    response = client.get("/torrents/abcdef123456")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Existing Torrent"
    assert data["download_url"] == "https://download.asdf.com/torrents/abc.torrent"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "completed"
