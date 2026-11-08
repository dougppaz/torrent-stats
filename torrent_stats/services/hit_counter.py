from __future__ import annotations

from datetime import UTC, datetime, timedelta

import redis
from torrent_stats.db.repository import TorrentMetadataRepository
from torrent_stats.settings import redis_settings
from torrent_stats.db.models import TorrentMetadata


class HitCounterService:
    def __init__(self) -> None:
        self.redis_client = redis.Redis.from_url(
            redis_settings.redis_url, decode_responses=True
        )
        self.torrent_repo = TorrentMetadataRepository()

    def record_hit(self, info_hash: str) -> tuple[int, str]:
        now = datetime.now(UTC)
        hour_str = now.strftime("%Y-%m-%d-%H")
        hit_key = f"torrent:hits:{info_hash}:{hour_str}"

        # Increment current hour bucket and set 12h TTL
        pipe = self.redis_client.pipeline()
        pipe.incr(hit_key)
        pipe.expire(hit_key, 12 * 3600)
        pipe.execute()

        # Collect past 12 hourly buckets
        keys_to_fetch = []
        for i in range(12):
            bucket_time = now - timedelta(hours=i)
            bucket_str = bucket_time.strftime("%Y-%m-%d-%H")
            keys_to_fetch.append(f"torrent:hits:{info_hash}:{bucket_str}")

        values = self.redis_client.mget(keys_to_fetch)
        total_hits = sum(int(v) for v in values if v is not None)
        last_hit_at = now.isoformat()

        # Sync to CouchDB metadata if exists
        torrent = self.torrent_repo.find_by_info_hash(info_hash)
        if torrent:
            torrent.total_hits = total_hits
            torrent.last_hit_at = last_hit_at
            self.torrent_repo.save(torrent)
        else:
            new_torrent = TorrentMetadata(
                info_hash=info_hash,
                total_hits=total_hits,
                last_hit_at=last_hit_at,
            )
            self.torrent_repo.save(new_torrent)

        return total_hits, last_hit_at


hit_counter_service = HitCounterService()
