from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel
from torrent_stats.db.client import couchdb_client
from torrent_stats.db.models import TorrentMetadata, WorkerKey

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    def __init__(self, model_class: type[T]) -> None:
        self.client = couchdb_client
        self.model_class = model_class

    def get(self, doc_id: str) -> T | None:
        raw = self.client.get_doc(doc_id)
        if not raw:
            return None
        res: T = self.model_class.model_validate(raw)
        return res

    def save(self, instance: T) -> T:
        data = instance.model_dump(by_alias=True)
        if (
            not data.get("_id")
            and hasattr(instance, "info_hash")
            and instance.info_hash
        ):
            data["_id"] = instance.info_hash
        elif not data.get("_id") and hasattr(instance, "id") and instance.id:
            data["_id"] = instance.id

        result = self.client.save_doc(data)
        data["_id"] = result.get("id", data.get("_id"))
        data["_rev"] = result.get("rev")
        res: T = self.model_class.model_validate(data)
        return res


class TorrentMetadataRepository(BaseRepository[TorrentMetadata]):
    def __init__(self) -> None:
        super().__init__(TorrentMetadata)

    def find_by_info_hash(self, info_hash: str) -> TorrentMetadata | None:
        return self.get(info_hash)


class WorkerKeyRepository(BaseRepository[WorkerKey]):
    def __init__(self) -> None:
        super().__init__(WorkerKey)

    def find_by_key_hash(self, key_hash: str) -> WorkerKey | None:
        docs = self.client.find_by_selector({"key_hash": key_hash})
        if docs:
            res: WorkerKey = self.model_class.model_validate(docs[0])
            return res
        return None
