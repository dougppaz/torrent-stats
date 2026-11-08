from __future__ import annotations

from typing import Generic, TypeVar

from torrent_stats.db.client import couchdb_client
from torrent_stats.db.models import StorageProfile, TorrentMetadata, WorkerKey

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, model_class: type[T]) -> None:
        self.client = couchdb_client
        self.model_class = model_class

    async def get(self, doc_id: str) -> T | None:
        raw = await self.client.get_doc(doc_id)
        if not raw:
            return None
        res: T = self.model_class.model_validate(raw)  # type: ignore[attr-defined]
        return res

    async def save(self, instance: T) -> T:
        data = instance.model_dump(by_alias=True)  # type: ignore[attr-defined]
        if not data.get("_id") and hasattr(instance, "infoHash") and instance.infoHash:
            data["_id"] = instance.infoHash
        elif not data.get("_id") and hasattr(instance, "id") and instance.id:
            data["_id"] = instance.id

        result = await self.client.save_doc(data)
        data["_id"] = result.get("id", data.get("_id"))
        data["_rev"] = result.get("rev")
        res: T = self.model_class.model_validate(data)  # type: ignore[attr-defined]
        return res


class TorrentMetadataRepository(BaseRepository[TorrentMetadata]):
    def __init__(self) -> None:
        super().__init__(TorrentMetadata)

    async def find_by_info_hash(self, info_hash: str) -> TorrentMetadata | None:
        return await self.get(info_hash)


class StorageProfileRepository(BaseRepository[StorageProfile]):
    def __init__(self) -> None:
        super().__init__(StorageProfile)


class WorkerKeyRepository(BaseRepository[WorkerKey]):
    def __init__(self) -> None:
        super().__init__(WorkerKey)

    async def find_by_key_hash(self, key_hash: str) -> WorkerKey | None:
        docs = await self.client.find_by_selector({"keyHash": key_hash})
        if docs:
            res: WorkerKey = self.model_class.model_validate(docs[0])
            return res
        return None
