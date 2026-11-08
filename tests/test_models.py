from torrent_stats.db.models import TorrentFile, TorrentMetadata, WorkerKey


def test_torrent_metadata_model():
    file_item = TorrentFile(path=["folder", "file.txt"], length=1024)
    meta = TorrentMetadata(
        info_hash="abcdef123456", name="Test Torrent", files=[file_item]
    )
    assert meta.info_hash == "abcdef123456"
    assert meta.name == "Test Torrent"
    assert meta.files is not None
    assert len(meta.files) == 1
    dump = meta.model_dump(by_alias=True)
    assert dump["_id"] == "abcdef123456"


def test_worker_key_model():
    wk = WorkerKey(key_hash="hash123", description="Test Worker")
    assert wk.key_hash == "hash123"
    assert wk.description == "Test Worker"
