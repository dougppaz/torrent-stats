from unittest.mock import MagicMock, patch

from torrent_stats.db.client import CouchDBClient


@patch("torrent_stats.db.client.couchdb.Server")
def test_couchdb_client(mock_server_cls):
    mock_server = MagicMock()
    mock_db = MagicMock()
    mock_server.__getitem__.return_value = mock_db
    mock_server_cls.return_value = mock_server

    client = CouchDBClient()
    db = client.get_db()
    assert db == mock_db

    client.ensure_db_exists()

    mock_db.get.return_value = {"_id": "doc1", "name": "test"}
    doc = client.get_doc("doc1")
    assert doc is not None
    assert doc["name"] == "test"

    mock_db.get.return_value = None
    assert client.get_doc("notfound") is None

    # Test save_doc when doc already in db
    mock_db.__contains__.return_value = True
    mock_db.save.return_value = ("doc1", "2-rev")
    res = client.save_doc({"_id": "doc1", "name": "updated"})
    assert res["ok"] is True

    # Test save_doc when doc not in db
    mock_db.__contains__.return_value = False
    res2 = client.save_doc({"name": "new"})
    assert res2["ok"] is True

    # Test save_doc with custom _id when doc not in db and _rev is None
    mock_db.__contains__.return_value = False
    mock_db.save.return_value = ("custom-id", "1-rev")
    res4 = client.save_doc({"_id": "custom-id", "name": "new3", "_rev": None})
    assert res4["ok"] is True
    assert res4["id"] == "custom-id"

    # Test find_by_selector
    mock_db.find.return_value = [{"_id": "doc1"}]
    found = client.find_by_selector({"name": "test"})
    assert len(found) == 1
