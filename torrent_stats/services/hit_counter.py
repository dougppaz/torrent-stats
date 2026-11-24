from __future__ import annotations

from datetime import UTC, datetime, timedelta

import redis
from torrent_stats.settings import redis_settings


class HitCounterService:
    def __init__(self) -> None:
        self.redis_client = redis.Redis.from_url(
            redis_settings.redis_url, decode_responses=True
        )

    def record_hit(self, info_hash: str, record_hit: bool = True) -> tuple[int, str]:
        now = datetime.now(UTC)
        hour_str = now.strftime("%Y-%m-%d-%H")
        hit_key = f"torrent:hits:{info_hash}:{hour_str}"
        last_hit_key = f"torrent:last_hit:{info_hash}"

        if record_hit:
            pipe = self.redis_client.pipeline()
            pipe.incr(hit_key)
            pipe.expire(hit_key, 12 * 3600)
            pipe.set(last_hit_key, now.isoformat())
            pipe.execute()

        total_hits = self.get_hits(info_hash)
        last_hit_val = self.redis_client.get(last_hit_key)
        last_hit_at = str(last_hit_val) if last_hit_val is not None else now.isoformat()

        return total_hits, last_hit_at

    def get_hits(self, info_hash: str) -> int:
        now = datetime.now(UTC)
        keys_to_fetch = []
        for i in range(12):
            bucket_time = now - timedelta(hours=i)
            bucket_str = bucket_time.strftime("%Y-%m-%d-%H")
            keys_to_fetch.append(f"torrent:hits:{info_hash}:{bucket_str}")

        values = self.redis_client.mget(keys_to_fetch)
        return sum(int(v) for v in values if v is not None)
