from __future__ import annotations

from unittest.mock import MagicMock

from torrent_stats.db.repository import (
    TaskRepository,
    TorrentMetadataRepository,
    WorkerKeyRepository,
)


def test_torrent_metadata_repository():
    mock_client = MagicMock()
    mock_client.get_doc.return_value = {
        "_id": "abc123hash",
        "info_hash": "abc123hash",
        "name": "Mock Torrent",
        "total_size": 2048,
        "total_hits": 5,
    }
    repo = TorrentMetadataRepository(client=mock_client)
    result = repo.find_by_info_hash("abc123hash")
    assert result is not None
    assert result.name == "Mock Torrent"
    assert result.total_hits == 5

    # Test get returning None
    mock_client.get_doc.return_value = None
    assert repo.get("notfound") is None

    mock_client.save_doc.return_value = {"id": "abc123hash", "rev": "1-rev"}
    saved = repo.save(result)
    assert saved.info_hash == "abc123hash"


def test_torrent_metadata_get_or_create():
    mock_client = MagicMock()
    repo = TorrentMetadataRepository(client=mock_client)
    # Case 1: exists
    mock_client.get_doc.return_value = {
        "_id": "abc123hash",
        "info_hash": "abc123hash",
        "name": "Existing",
    }
    mock_client.save_doc.return_value = {"id": "abc123hash", "rev": "2-rev"}
    torrent, created = repo.get_or_create("abc123hash", total_hits=3, last_hit_at="now")
    assert not created
    assert torrent.total_hits == 3

    # Case 2: does not exist
    mock_client.get_doc.return_value = None
    torrent, created = repo.get_or_create("newhash", total_hits=1, last_hit_at="now")
    assert created
    assert torrent.info_hash == "newhash"


def test_worker_key_repository():
    mock_client = MagicMock()
    repo = WorkerKeyRepository(client=mock_client)
    mock_client.save_doc.return_value = {"id": "hash", "rev": "1-rev"}
    wk = repo.save_key("raw-key", "worker 1")
    assert wk.key_hash is not None

    mock_client.find_by_selector.return_value = [
        {"_id": "hash", "key_hash": wk.key_hash, "description": "worker 1"}
    ]
    found = repo.find_by_key_hash("raw-key")
    assert found is not None
    assert found.description == "worker 1"

    # Test find_by_key_hash returning None
    mock_client.find_by_selector.return_value = []
    assert repo.find_by_key_hash("unknown-key") is None


def test_task_repository_find_claimable():
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.get_db.return_value = mock_db

    row1 = MagicMock()
    row1.doc = {"_id": "t1", "info_hash": "abc", "status": "pending"}
    row2 = MagicMock()
    row2.doc = {
        "_id": "t2",
        "info_hash": "def",
        "status": "claimed",
        "lease_expires_at": "2020-01-01T00:00:00Z",
    }

    mock_db.view.side_effect = [[row1], [row2], []]

    repo = TaskRepository(client=mock_client)
    tasks = repo.find_claimable()
    assert len(tasks) == 2
    assert tasks[0].id == "t1"
    assert tasks[1].id == "t2"


def test_task_repository_find_claimable_fallback():
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.get_db.return_value = mock_db

    mock_db.view.side_effect = Exception("view error")
    mock_db.__iter__.return_value = ["t1"]
    mock_db.get.return_value = {"_id": "t1", "info_hash": "abc", "status": "pending"}

    repo = TaskRepository(client=mock_client)
    tasks = repo.find_claimable()
    assert len(tasks) == 1
    assert tasks[0].id == "t1"
