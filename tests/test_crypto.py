from torrent_stats.db.crypto import hash_worker_key


def test_hash_worker_key():
    key = "secret-worker-key"
    hashed1 = hash_worker_key(key)
    hashed2 = hash_worker_key(key)
    assert hashed1 == hashed2
    assert len(hashed1) == 64  # SHA256 hexdigest length
    assert hashed1 != key
