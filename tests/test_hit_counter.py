from __future__ import annotations

from unittest.mock import MagicMock, patch

from torrent_stats.services.hit_counter import HitCounterService


@patch("torrent_stats.services.hit_counter.redis.Redis")
def test_hit_counter_service_existing(mock_redis_cls):
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.mget.return_value = ["3", "2", None, "1"]
    mock_redis.get.return_value = "2026-11-07T00:00:00Z"
    mock_redis_cls.from_url.return_value = mock_redis

    service = HitCounterService()
    total_hits, last_hit_at = service.record_hit("hash123", record_hit=True)

    assert total_hits == 6
    assert last_hit_at == "2026-11-07T00:00:00Z"
    mock_pipe.incr.assert_called_once()
    mock_pipe.set.assert_called_once()
    mock_pipe.execute.assert_called_once()


@patch("torrent_stats.services.hit_counter.redis.Redis")
def test_hit_counter_service_no_record(mock_redis_cls):
    mock_redis = MagicMock()
    mock_redis.mget.return_value = ["1"]
    mock_redis.get.return_value = "2026-11-07T00:00:00Z"
    mock_redis_cls.from_url.return_value = mock_redis

    service = HitCounterService()
    total_hits, last_hit_at = service.record_hit("hash_new", record_hit=False)

    assert total_hits == 1
    assert last_hit_at == "2026-11-07T00:00:00Z"
    mock_redis.pipeline.assert_not_called()
