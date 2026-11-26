from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from torrent_stats.db.models import (
    TaskDocument,
    TorrentMetadata,
    TrackerStatDocument,
)
from torrent_stats.interfaces.api.depends import (
    get_hit_counter_service,
    get_storage_manager,
    get_task_repository,
    get_torrent_repository,
    get_tracker_stats_repository,
)
from torrent_stats.interfaces.api.main import app

client = TestClient(app)

VALID_HASH = "abcdef1234567890abcdef1234567890abcdef12"


def test_get_torrent_endpoint_missing():
    mock_repo = MagicMock = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = MagicMock()
    mock_hit_counter = MagicMock()
    mock_storage = MagicMock()

    mock_hit_counter.record_hit.return_value = (
        10,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(info_hash=VALID_HASH)
    mock_repo.get_or_create.return_value = (meta, True)
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(info_hash=VALID_HASH, task_type="scrape_torrent", status="pending")
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get(
            f"/torrents/{VALID_HASH}?trackers=udp://tracker.opentrackr.org:1337"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["info_hash"] == VALID_HASH
    assert data["total_hits"] == 10
    assert data["download_url"] is None
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "pending"


def test_get_torrent_endpoint_existing():
    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (
        5,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(
        info_hash=VALID_HASH,
        name="Existing Torrent",
        total_size=1024,
        storage_profile_key="ftp",
        storage_params={"file_path": "torrents/abc.torrent"},
    )
    mock_repo.get_or_create.return_value = (meta, False)
    mock_storage.get_download_url.return_value = (
        "https://download.asdf.com/torrents/abc.torrent"
    )
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            info_hash=VALID_HASH, task_type="scrape_torrent", status="completed"
        )
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get(f"/torrents/{VALID_HASH}")
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

    mock_hit_counter.record_hit.return_value = (
        1,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(info_hash=VALID_HASH)
    mock_repo.get_or_create.return_value = (meta, True)
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(info_hash=VALID_HASH, task_type="scrape_torrent", status="pending")
    ]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage
    mock_tracker_stats_repo = __import__("unittest.mock").mock.MagicMock()
    mock_tracker_stats_repo.find_by_info_hash.return_value = [
        TrackerStatDocument(
            info_hash=VALID_HASH, tracker_url="udp://default.tracker:1337"
        )
    ]
    app.dependency_overrides[get_tracker_stats_repository] = lambda: (
        mock_tracker_stats_repo
    )

    try:
        response = client.get(f"/torrents/{VALID_HASH}")
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

    mock_hit_counter.record_hit.return_value = (
        1,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(info_hash=VALID_HASH)
    mock_repo.get_or_create.return_value = (meta, False)
    mock_task_repo.find_by_info_hash.return_value = [
        TaskDocument(
            info_hash=VALID_HASH,
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
        response = client.get(f"/torrents/{VALID_HASH}")
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


def test_get_torrent_invalid_info_hash():
    response = client.get("/torrents/short")
    assert response.status_code == 422


def test_get_torrent_renew_failed_scrape_torrent_cooldown_expired():
    from datetime import timedelta

    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (
        1,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(info_hash=VALID_HASH)
    mock_repo.get_or_create.return_value = (meta, False)

    past = datetime.now(UTC) - timedelta(hours=15)
    old_task = TaskDocument(
        _id="task-old",
        info_hash=VALID_HASH,
        task_type="scrape_torrent",
        status="failed",
        last_attempt_at=past,
    )
    mock_task_repo.find_by_info_hash.return_value = [old_task]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get(f"/torrents/{VALID_HASH}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_task_repo.delete.assert_not_called()
    mock_task_repo.save.assert_called()


def test_get_torrent_no_renew_failed_scrape_torrent_cooldown_active():
    from datetime import timedelta

    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (
        1,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(info_hash=VALID_HASH)
    mock_repo.get_or_create.return_value = (meta, False)

    recent = datetime.now(UTC) - timedelta(minutes=10)
    old_task = TaskDocument(
        _id="task-old",
        info_hash=VALID_HASH,
        task_type="scrape_torrent",
        status="failed",
        last_attempt_at=recent,
    )
    mock_task_repo.find_by_info_hash.return_value = [old_task]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get(f"/torrents/{VALID_HASH}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_task_repo.delete.assert_not_called()


def test_get_torrent_no_renew_completed_scrape_torrent():
    from datetime import timedelta

    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (
        1,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(info_hash=VALID_HASH)
    mock_repo.get_or_create.return_value = (meta, False)

    past = datetime.now(UTC) - timedelta(hours=20)
    completed_task = TaskDocument(
        _id="task-completed",
        info_hash=VALID_HASH,
        task_type="scrape_torrent",
        status="completed",
        last_attempt_at=past,
    )
    mock_task_repo.find_by_info_hash.return_value = [completed_task]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage

    try:
        response = client.get(f"/torrents/{VALID_HASH}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_task_repo.delete.assert_not_called()


def test_get_torrent_renew_scrape_stats_cooldown_expired():
    from datetime import timedelta

    mock_repo = __import__("unittest.mock").mock.MagicMock()
    mock_task_repo = __import__("unittest.mock").mock.MagicMock()
    mock_hit_counter = __import__("unittest.mock").mock.MagicMock()
    mock_storage = __import__("unittest.mock").mock.MagicMock()

    mock_hit_counter.record_hit.return_value = (
        1,
        datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC),
    )
    meta = TorrentMetadata(
        info_hash=VALID_HASH,
    )
    mock_repo.get_or_create.return_value = (meta, False)

    past = datetime.now(UTC) - timedelta(hours=7)
    stats_task = TaskDocument(
        _id="task-stats",
        info_hash=VALID_HASH,
        task_type="scrape_stats",
        status="completed",
        tracker_url="udp://tracker:1337",
        tracker_updated_at=past,
    )
    torrent_scrape = TaskDocument(
        _id="task-scrape",
        info_hash=VALID_HASH,
        task_type="scrape_torrent",
        status="completed",
    )
    mock_task_repo.find_by_info_hash.return_value = [torrent_scrape, stats_task]

    app.dependency_overrides[get_torrent_repository] = lambda: mock_repo
    app.dependency_overrides[get_task_repository] = lambda: mock_task_repo
    app.dependency_overrides[get_hit_counter_service] = lambda: mock_hit_counter
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage
    mock_tracker_stats_repo = __import__("unittest.mock").mock.MagicMock()
    mock_tracker_stats_repo.find_by_info_hash.return_value = [
        TrackerStatDocument(
            info_hash=VALID_HASH, tracker_url="udp://tracker:1337", seeds=1, peers=1
        )
    ]
    app.dependency_overrides[get_tracker_stats_repository] = lambda: (
        mock_tracker_stats_repo
    )

    try:
        response = client.get(f"/torrents/{VALID_HASH}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_task_repo.delete.assert_not_called()
    mock_task_repo.save.assert_called()
