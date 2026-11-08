from unittest.mock import MagicMock, patch

from torrent_stats.db.models import TorrentMetadata
from torrent_stats.services.hit_counter import HitCounterService


@patch("torrent_stats.services.hit_counter.redis.Redis")
@patch("torrent_stats.services.hit_counter.TorrentMetadataRepository")
def test_hit_counter_service_existing(mock_repo_cls, mock_redis_cls):
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.mget.return_value = ["3", "2", None, "1"]
    mock_redis_cls.from_url.return_value = mock_redis

    mock_repo = MagicMock()
    mock_repo.find_by_info_hash.return_value = TorrentMetadata(
        info_hash="hash123", total_hits=5
    )
    mock_repo_cls.return_value = mock_repo

    service = HitCounterService()
    total_hits, last_hit_at = service.record_hit("hash123")

    assert total_hits == 6
    assert last_hit_at is not None
    mock_pipe.incr.assert_called_once()
    mock_pipe.execute.assert_called_once()
    mock_repo.save.assert_called()


@patch("torrent_stats.services.hit_counter.redis.Redis")
@patch("torrent_stats.services.hit_counter.TorrentMetadataRepository")
def test_hit_counter_service_new(mock_repo_cls, mock_redis_cls):
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.mget.return_value = ["1"]
    mock_redis_cls.from_url.return_value = mock_redis

    mock_repo = MagicMock()
    mock_repo.find_by_info_hash.return_value = None
    mock_repo_cls.return_value = mock_repo

    service = HitCounterService()
    total_hits, last_hit_at = service.record_hit("hash_new")

    assert total_hits == 1
    assert last_hit_at is not None
    mock_repo.save.assert_called()
