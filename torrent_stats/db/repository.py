from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel
from torrent_stats.db.client import CouchDBClient
from torrent_stats.db.crypto import hash_worker_key
from torrent_stats.db.models import (
    TaskDocument,
    TorrentMetadata,
    TrackerStatDocument,
    WorkerKey,
)

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    def __init__(self, model_class: type[T], client: CouchDBClient) -> None:
        self.client = client
        self.model_class = model_class

    def get(self, doc_id: str) -> T | None:
        raw = self.client.get_doc(doc_id)
        if not raw:
            return None
        res: T = self.model_class.model_validate(raw)
        return res

    def save(self, instance: T) -> T:
        data = instance.model_dump(mode="json", by_alias=True)
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

    def delete(self, doc_id: str) -> bool:
        db = self.client.get_db()
        doc = db.get(doc_id)
        if doc:
            db.delete(doc)
            return True
        return False


class TorrentMetadataRepository(BaseRepository[TorrentMetadata]):
    def __init__(self, client: CouchDBClient) -> None:
        super().__init__(TorrentMetadata, client=client)

    def find_by_info_hash(self, info_hash: str) -> TorrentMetadata | None:
        return self.get(info_hash)

    def get_or_create(self, info_hash: str) -> tuple[TorrentMetadata, bool]:
        torrent = self.find_by_info_hash(info_hash)
        if torrent:
            return torrent, False
        else:
            torrent = TorrentMetadata(info_hash=info_hash)
            saved = self.save(torrent)
            return saved, True


class WorkerKeyRepository(BaseRepository[WorkerKey]):
    def __init__(self, client: CouchDBClient) -> None:
        super().__init__(WorkerKey, client=client)

    def save_key(self, raw_key: str, description: str = "") -> WorkerKey:
        if not description or not description.strip():
            now_str = datetime.now(UTC).isoformat()
            description = f"Worker Key created at {now_str}"
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
    def __init__(self, client: CouchDBClient) -> None:
        super().__init__(TaskDocument, client=client)
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

    def update_task_status(
        self,
        task_id: str,
        status: str,
        lease_expires_at: datetime | None = None,
        claimed_at: datetime | None = None,
        last_attempt_at: datetime | None = None,
        error_message: str | None = None,
    ) -> TaskDocument | None:
        task = self.get(task_id)
        if not task:
            return None
        task.status = status
        now = datetime.now(UTC)
        task.updated_at = now
        if lease_expires_at is not None:
            task.lease_expires_at = lease_expires_at
        if claimed_at is not None:
            task.claimed_at = claimed_at
        if last_attempt_at is not None:
            task.last_attempt_at = last_attempt_at
        if error_message is not None:
            task.error_message = error_message
        return self.save(task)


class TrackerStatsRepository(BaseRepository[TrackerStatDocument]):
    def __init__(self, client: CouchDBClient) -> None:
        super().__init__(TrackerStatDocument, client=client)

    def find_by_info_hash(self, info_hash: str) -> list[TrackerStatDocument]:
        docs = self.client.find_by_selector({"info_hash": info_hash})
        return [TrackerStatDocument.model_validate(doc) for doc in docs]

    def find_by_info_hash_and_tracker(
        self, info_hash: str, tracker_url: str
    ) -> TrackerStatDocument | None:
        docs = self.client.find_by_selector(
            {"info_hash": info_hash, "tracker_url": tracker_url}
        )
        if docs:
            return TrackerStatDocument.model_validate(docs[0])
        return None

    def get_or_create(
        self, info_hash: str, tracker_url: str
    ) -> tuple[TrackerStatDocument, bool]:
        existing = self.find_by_info_hash_and_tracker(info_hash, tracker_url)
        if existing:
            return existing, False
        doc = TrackerStatDocument(info_hash=info_hash, tracker_url=tracker_url)
        saved = self.save(doc)
        return saved, True

    def update_stats(
        self, info_hash: str, tracker_url: str, seeds: int, peers: int
    ) -> TrackerStatDocument:
        doc = self.find_by_info_hash_and_tracker(info_hash, tracker_url)
        now = datetime.now(UTC)
        if doc:
            doc.seeds = seeds
            doc.peers = peers
            doc.updated_at = now
            doc.consecutive_failures = 0
            return self.save(doc)
        else:
            doc = TrackerStatDocument(
                info_hash=info_hash,
                tracker_url=tracker_url,
                seeds=seeds,
                peers=peers,
                updated_at=now,
                consecutive_failures=0,
            )
            return self.save(doc)

    def increment_failure(
        self, info_hash: str, tracker_url: str
    ) -> TrackerStatDocument:
        doc = self.find_by_info_hash_and_tracker(info_hash, tracker_url)
        now = datetime.now(UTC)
        if doc:
            doc.consecutive_failures += 1
            doc.updated_at = now
            return self.save(doc)
        else:
            doc = TrackerStatDocument(
                info_hash=info_hash,
                tracker_url=tracker_url,
                seeds=0,
                peers=0,
                updated_at=now,
                consecutive_failures=1,
            )
            return self.save(doc)
