from __future__ import annotations

import hashlib
import hmac

from torrent_stats.settings import worker_settings


def hash_worker_key(raw_key: str) -> str:
    salt = worker_settings.worker_key_salt.encode("utf-8")
    key_bytes = raw_key.encode("utf-8")
    return hmac.new(salt, key_bytes, hashlib.sha256).hexdigest()
