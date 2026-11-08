from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel
from torrent_stats.db.client import CouchDBClient, couchdb_client
from torrent_stats.db.crypto import hash_worker_key
from torrent_stats.db.models import TaskDocument, TorrentMetadata, WorkerKey
from torrent_stats.settings import couchdb_settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


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

    def get_or_create(
        self, info_hash: str, total_hits: int = 0, last_hit_at: str | None = None
    ) -> tuple[TorrentMetadata, bool]:
        torrent = self.find_by_info_hash(info_hash)
        if torrent:
            torrent.total_hits = total_hits
            torrent.last_hit_at = last_hit_at
            saved = self.save(torrent)
            return saved, False
        else:
            torrent = TorrentMetadata(
                info_hash=info_hash,
                total_hits=total_hits,
                last_hit_at=last_hit_at,
            )
            saved = self.save(torrent)
            return saved, True


class WorkerKeyRepository(BaseRepository[WorkerKey]):
    def __init__(self) -> None:
        super().__init__(WorkerKey)

    def save_key(self, raw_key: str, description: str = "") -> WorkerKey:
        hashed = hash_worker_key(raw_key)
        worker_key = WorkerKey(_id=hashed, key_hash=hashed, description=description)
        return self.save(worker_key)

    def find_by_key_hash(self, raw_key: str) -> WorkerKey | None:
        hashed = hash_worker_key(raw_key)
        docs = self.client.find_by_selector({"key_hash": hashed})
        if docs:
            res: WorkerKey = self.model_class.model_validate(docs[0])
            return res
        return None


class TaskRepository(BaseRepository[TaskDocument]):
    def __init__(self) -> None:
        super().__init__(TaskDocument)
        self.client = CouchDBClient(db_name=f"{couchdb_settings.couchdb_db_name}_tasks")
        self.ensure_view_exists()

    def ensure_view_exists(self) -> None:
        try:
            db = self.client.get_db()
            design_id = "_design/tasks"
            doc = db.get(design_id)
            view_map = """
            function(doc) {
                if (doc.status) {
                    var lease = doc.lease_expires_at ? doc.lease_expires_at : "";
                    emit([doc.status, lease], null);
                }
            }
            """
            if not doc:
                db.save({"_id": design_id, "views": {"claimable": {"map": view_map}}})
            elif "views" not in doc or "claimable" not in doc["views"]:
                doc["views"] = {"claimable": {"map": view_map}}
                db.save(doc)
        except Exception:
            logger.debug("Failed to ensure tasks view exists", exc_info=True)

    def find_by_info_hash(self, info_hash: str) -> list[TaskDocument]:
        docs = self.client.find_by_selector({"info_hash": info_hash})
        if not docs:
            db = self.client.get_db()
            docs = [db.get(doc_id) for doc_id in db if not doc_id.startswith("_")]
            docs = [d for d in docs if d and d.get("info_hash") == info_hash]
        return [TaskDocument.model_validate(d) for d in docs if d]

    def find_claimable(self) -> list[TaskDocument]:
        now_iso = datetime.now(UTC).isoformat()
        try:
            db = self.client.get_db()
            docs = []

            res_pending = db.view(
                "tasks/claimable",
                startkey=["pending", ""],
                endkey=["pending", {}],
                include_docs=True,
            )
            for row in res_pending:
                if row.doc:
                    docs.append(row.doc)

            res_claimed = db.view(
                "tasks/claimable",
                startkey=["claimed", ""],
                endkey=["claimed", now_iso],
                include_docs=True,
            )
            for row in res_claimed:
                if row.doc:
                    docs.append(row.doc)

            res_scraping = db.view(
                "tasks/claimable",
                startkey=["scraping", ""],
                endkey=["scraping", now_iso],
                include_docs=True,
            )
            for row in res_scraping:
                if row.doc:
                    docs.append(row.doc)

            return [TaskDocument.model_validate(dict(d)) for d in docs]
        except Exception:
            logger.debug(
                "Failed to query tasks/claimable view, falling back", exc_info=True
            )
            db = self.client.get_db()
            all_docs = [db.get(doc_id) for doc_id in db if not doc_id.startswith("_")]
            return [TaskDocument.model_validate(d) for d in all_docs if d is not None]
