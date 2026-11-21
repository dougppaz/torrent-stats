from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from torrent_stats.db.models import (
    TaskDocument,
    TorrentMetadata,
    TrackerStat,
    WorkerKey,
)
from torrent_stats.interfaces.api.depends import (
    get_storage_manager,
    get_task_repository,
    get_torrent_repository,
    get_worker_key_repository,
)
from torrent_stats.interfaces.api.main import app

client = TestClient(app)

VALID_HASH = "abcdef1234567890abcdef1234567890abcdef12"


def test_worker_unauthorized():
    mock_worker_key_repo = MagicMock()
    mock_worker_key_repo.find_by_key_hash.return_value = None
    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo

    try:
        response = client.post(
            "/worker/tasks/claim", headers={"X-Worker-Key": "invalid-key"}
        )
        assert response.status_code == 401

        response2 = client.post("/worker/tasks/claim")
        assert response2.status_code == 401
    finally:
        app.dependency_overrides.clear()


@patch("torrent_stats.interfaces.api.routers.worker.worker_settings")
def test_worker_allow_any_key(mock_worker_settings):
    mock_task_repo = MagicMock()
    mock_worker_settings.worker_allow_any_key = True
    mock_task_repo.find_claimable.return_value = []

    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo

    try:
        response = client.post(
            "/worker/tasks/claim", headers={"X-Worker-Key": "any-random-key"}
        )
        assert response.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_worker_claim_task_no_content():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    mock_task_repo.find_claimable.return_value = []

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo

    try:
        response = client.post(
            "/worker/tasks/claim", headers={"X-Worker-Key": "valid-key"}
        )
        assert response.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_worker_claim_task_success():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    task = TaskDocument(
        _id="task-1",
        info_hash="abc123456",
        task_type="scrape_torrent",
        status="pending",
    )
    mock_task_repo.find_claimable.return_value = [task]

    def update_mock_task(
        task_id: str,
        status: str,
        lease_expires_at: str | None = None,
        claimed_at: str | None = None,
        last_attempt_at: str | None = None,
        error_message: str | None = None,
    ) -> TaskDocument:
        task.status = status
        if lease_expires_at:
            task.lease_expires_at = lease_expires_at
        if claimed_at:
            task.claimed_at = claimed_at
        if last_attempt_at:
            task.last_attempt_at = last_attempt_at
        if error_message:
            task.error_message = error_message
        return task

    mock_task_repo.update_task_status.side_effect = update_mock_task

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo

    try:
        response = client.post(
            "/worker/tasks/claim", headers={"X-Worker-Key": "valid-key"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-1"
    assert data["info_hash"] == "abc123456"
    assert data["task_type"] == "scrape_torrent"
    assert "lease_expires_at" in data


def test_worker_claim_task_expired_lease_and_cooldowns():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_torrent_repo = MagicMock()

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
    )
    mock_torrent_repo.find_by_info_hash.return_value = torrent

    task_expired = TaskDocument(
        _id="task-expired",
        info_hash="abc999",
        task_type="scrape_torrent",
        status="claimed",
        lease_expires_at=past,
    )
    task_fresh_stats = TaskDocument(
        _id="task-fresh-stats",
        info_hash="abc999",
        task_type="scrape_stats",
        status="pending",
        tracker_url="udp://tracker:1337",
    )
    mock_task_repo.find_claimable.return_value = [task_expired, task_fresh_stats]

    def update_mock_expired(
        task_id: str,
        status: str,
        lease_expires_at: str | None = None,
        claimed_at: str | None = None,
        last_attempt_at: str | None = None,
        error_message: str | None = None,
    ) -> TaskDocument:
        task_expired.status = status
        if lease_expires_at:
            task_expired.lease_expires_at = lease_expires_at
        if claimed_at:
            task_expired.claimed_at = claimed_at
        if last_attempt_at:
            task_expired.last_attempt_at = last_attempt_at
        if error_message:
            task_expired.error_message = error_message
        return task_expired

    mock_task_repo.update_task_status.side_effect = update_mock_expired

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_torrent_repository] = lambda: mock_torrent_repo

    try:
        response = client.post(
            "/worker/tasks/claim", headers={"X-Worker-Key": "valid-key"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "task-expired"


def test_worker_upload_torrent_full():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_torrent_repo = MagicMock()
    mock_storage_manager = MagicMock()

    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    mock_storage_manager.upload_torrent.return_value = (
        "ftp",
        {"file_path": f"{VALID_HASH}.torrent"},
        f"ftp://server/{VALID_HASH}.torrent",
    )
    mock_torrent_repo.find_by_info_hash.return_value = None
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            _id="task-abc",
            info_hash=VALID_HASH,
            task_type="scrape_torrent",
            status="pending",
        )
    ]

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_torrent_repository] = lambda: mock_torrent_repo
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage_manager

    try:
        response = client.post(
            "/worker/torrents",
            headers={"X-Worker-Key": "valid-key"},
            data={
                "info_hash": VALID_HASH,
                "name": "Test Torrent",
                "total_size": 2048,
                "storage_profile_key": "ftp",
                "storage_params": '{"custom": "val"}',
                "files": '[{"path": "file.txt", "length": 2048}]',
            },
            files={"torrent_file": ("test.torrent", b"d8:announce...")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["info_hash"] == VALID_HASH


def test_worker_submit_tracker_stats_and_prune():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_torrent_repo = MagicMock()

    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    torrent = TorrentMetadata(
        info_hash=VALID_HASH,
        tracker_stats=[
            TrackerStat(tracker_url="udp://tracker.test:1337", consecutive_failures=2)
        ],
    )
    mock_torrent_repo.find_by_info_hash.return_value = torrent
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            _id="task-stats",
            info_hash=VALID_HASH,
            task_type="scrape_stats",
            tracker_url="udp://tracker.test:1337",
            status="claimed",
        )
    ]

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_torrent_repository] = lambda: mock_torrent_repo

    try:
        # Submit failure (3rd consecutive failure -> should prune)
        response = client.post(
            f"/worker/torrents/{VALID_HASH}/stats",
            headers={"X-Worker-Key": "valid-key"},
            json={"tracker_url": "udp://tracker.test:1337", "success": False},
        )
        assert response.status_code == 200
        assert len(torrent.tracker_stats) == 0

        # Submit success for new tracker
        response2 = client.post(
            f"/worker/torrents/{VALID_HASH}/stats",
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
            f"/worker/torrents/{VALID_HASH}/stats",
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
            f"/worker/torrents/{VALID_HASH}/stats",
            headers={"X-Worker-Key": "valid-key"},
            json={"tracker_url": "udp://tracker.fail:1337", "success": False},
        )
        assert response4.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_worker_task_fail_success():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    task = TaskDocument(
        _id="task-fail-1",
        info_hash=VALID_HASH,
        task_type="scrape_torrent",
        status="claimed",
    )
    mock_task_repo.get.return_value = task

    def update_mock_fail(
        task_id: str,
        status: str,
        lease_expires_at: str | None = None,
        claimed_at: str | None = None,
        last_attempt_at: str | None = None,
        error_message: str | None = None,
    ) -> TaskDocument:
        task.status = status
        if lease_expires_at:
            task.lease_expires_at = lease_expires_at
        if claimed_at:
            task.claimed_at = claimed_at
        if last_attempt_at:
            task.last_attempt_at = last_attempt_at
        if error_message:
            task.error_message = error_message
        return task

    mock_task_repo.update_task_status.side_effect = update_mock_fail

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo

    try:
        response = client.post(
            "/worker/tasks/task-fail-1/fail",
            headers={"X-Worker-Key": "valid-key"},
            json={"error_message": "not implemented"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["info_hash"] == VALID_HASH
    assert task.status == "failed"
    assert task.error_message == "not implemented"


def test_worker_task_fail_not_found():
    mock_worker_key_repo = MagicMock()
    mock_task_repo = MagicMock()
    mock_worker_key_repo.find_by_key_hash.return_value = WorkerKey(
        _id="hash1", key_hash="hash1"
    )
    mock_task_repo.get.return_value = None

    app.dependency_overrides[get_worker_key_repository] = lambda: mock_worker_key_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo

    try:
        response = client.post(
            "/worker/tasks/nonexistent/fail",
            headers={"X-Worker-Key": "valid-key"},
            json={"error_message": "not implemented"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
