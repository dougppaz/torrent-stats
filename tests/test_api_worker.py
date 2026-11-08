from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from torrent_stats.db.models import TaskItem, TorrentMetadata, TrackerStat, WorkerKey
from torrent_stats.main import app

client = TestClient(app)


@patch("torrent_stats.api.routers.worker.worker_key_repo")
def test_worker_unauthorized(mock_worker_key_repo):
    mock_worker_key_repo.find_by_key_hash.return_value = None

    response = client.post(
        "/worker/tasks/claim", headers={"X-Worker-Key": "invalid-key"}
    )
    assert response.status_code == 401

    response2 = client.post("/worker/tasks/claim")
    assert response2.status_code == 401


@patch("torrent_stats.api.routers.worker.worker_key_repo")
@patch("torrent_stats.api.routers.worker.torrent_repo")
def test_worker_claim_task_no_content(mock_torrent_repo, mock_worker_key_repo):
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    mock_db: dict[str, Any] = {}
    mock_torrent_repo.client.get_db.return_value = mock_db

    response = client.post("/worker/tasks/claim", headers={"X-Worker-Key": "valid-key"})
    assert response.status_code == 204


@patch("torrent_stats.api.routers.worker.worker_key_repo")
@patch("torrent_stats.api.routers.worker.torrent_repo")
def test_worker_claim_task_success(mock_torrent_repo, mock_worker_key_repo):
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    torrent = TorrentMetadata(
        info_hash="abc123456",
        tasks=[
            TaskItem(task_id="task-1", task_type="scrape_torrent", status="pending")
        ],
    )
    mock_db: dict[str, Any] = {"abc123456": torrent.model_dump(by_alias=True)}
    mock_torrent_repo.client.get_db.return_value = mock_db
    mock_torrent_repo.find_by_info_hash.return_value = torrent

    response = client.post("/worker/tasks/claim", headers={"X-Worker-Key": "valid-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-1"
    assert data["info_hash"] == "abc123456"
    assert data["task_type"] == "scrape_torrent"
    assert "lease_expires_at" in data


@patch("torrent_stats.api.routers.worker.worker_key_repo")
@patch("torrent_stats.api.routers.worker.torrent_repo")
def test_worker_claim_task_expired_lease_and_cooldowns(
    mock_torrent_repo, mock_worker_key_repo
):
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    recent = datetime.now(UTC).isoformat()

    torrent = TorrentMetadata(
        info_hash="abc999",
        tracker_stats=[
            TrackerStat(tracker_url="udp://tracker:1337", updated_at=recent)
        ],
        tasks=[
            TaskItem(
                task_id="task-expired",
                task_type="scrape_torrent",
                status="claimed",
                lease_expires_at=past,
            ),
            TaskItem(
                task_id="task-fresh-stats",
                task_type="scrape_stats",
                status="pending",
            ),
        ],
    )
    mock_db: dict[str, Any] = {"abc999": torrent.model_dump(by_alias=True)}
    mock_torrent_repo.client.get_db.return_value = mock_db

    response = client.post("/worker/tasks/claim", headers={"X-Worker-Key": "valid-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-expired"


@patch("torrent_stats.api.routers.worker.worker_key_repo")
@patch("torrent_stats.api.routers.worker.torrent_repo")
@patch("torrent_stats.api.routers.worker.storage_manager")
def test_worker_upload_torrent_full(
    mock_storage_manager, mock_torrent_repo, mock_worker_key_repo
):
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    mock_storage_manager.upload_torrent.return_value = (
        "ftp",
        {"file_path": "abc123.torrent"},
        "ftp://server/abc123.torrent",
    )
    mock_torrent_repo.find_by_info_hash.return_value = None

    response = client.post(
        "/worker/torrents",
        headers={"X-Worker-Key": "valid-key"},
        data={
            "info_hash": "abc123",
            "name": "Test Torrent",
            "total_size": 2048,
            "storage_profile_key": "ftp",
            "storage_params": '{"custom": "val"}',
            "files": '[{"path": ["file.txt"], "length": 2048}]',
        },
        files={"torrent_file": ("test.torrent", b"d8:announce...")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["info_hash"] == "abc123"


@patch("torrent_stats.api.routers.worker.worker_key_repo")
@patch("torrent_stats.api.routers.worker.torrent_repo")
def test_worker_submit_tracker_stats_and_prune(mock_torrent_repo, mock_worker_key_repo):
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    torrent = TorrentMetadata(
        info_hash="abc123",
        tracker_stats=[
            TrackerStat(tracker_url="udp://tracker.test:1337", consecutive_failures=2)
        ],
    )
    mock_torrent_repo.find_by_info_hash.return_value = torrent

    # Submit failure (3rd consecutive failure -> should prune)
    response = client.post(
        "/worker/torrents/abc123/stats",
        headers={"X-Worker-Key": "valid-key"},
        json={"tracker_url": "udp://tracker.test:1337", "success": False},
    )
    assert response.status_code == 200
    assert len(torrent.tracker_stats) == 0

    # Submit success for new tracker
    response2 = client.post(
        "/worker/torrents/abc123/stats",
        headers={"X-Worker-Key": "valid-key"},
        json={
            "tracker_url": "udp://tracker.new:1337",
            "success": True,
            "seeds": 10,
            "peers": 5,
        },
    )
    assert response2.status_code == 200

    # Submit success for existing tracker
    response3 = client.post(
        "/worker/torrents/abc123/stats",
        headers={"X-Worker-Key": "valid-key"},
        json={
            "tracker_url": "udp://tracker.new:1337",
            "success": True,
            "seeds": 15,
            "peers": 8,
        },
    )
    assert response3.status_code == 200

    # Submit failure for new tracker
    response4 = client.post(
        "/worker/torrents/abc123/stats",
        headers={"X-Worker-Key": "valid-key"},
        json={"tracker_url": "udp://tracker.fail:1337", "success": False},
    )
    assert response4.status_code == 200
