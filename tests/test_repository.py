from unittest.mock import patch

from torrent_stats.db.repository import (
    TorrentMetadataRepository,
    WorkerKeyRepository,
)


@patch("torrent_stats.db.repository.couchdb_client")
def test_torrent_metadata_repository(mock_client):
    mock_client.get_doc.return_value = {
        "_id": "abc123hash",
        "info_hash": "abc123hash",
        "name": "Mock Torrent",
        "total_size": 2048,
        "total_hits": 5,
    }
    repo = TorrentMetadataRepository()
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


@patch("torrent_stats.db.repository.couchdb_client")
def test_worker_key_repository(mock_client):
    repo = WorkerKeyRepository()
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
