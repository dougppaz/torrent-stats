from __future__ import annotations

from typing import Any

import couchdb
from torrent_stats.settings import couchdb_settings


class CouchDBClient:
    def __init__(self) -> None:
        self.server = couchdb.Server(couchdb_settings.couchdb_url)
        self.db_name = couchdb_settings.couchdb_db_name

    def get_db(self) -> couchdb.Database:
        try:
            return self.server[self.db_name]
        except couchdb.ResourceNotFound:
            return self.server.create(self.db_name)

    def ensure_db_exists(self) -> None:
        self.get_db()

    def get_doc(self, doc_id: str) -> dict[str, Any] | None:
        db = self.get_db()
        doc = db.get(doc_id)
        if doc:
            return dict(doc)
        return None

    def save_doc(self, doc: dict[str, Any]) -> dict[str, Any]:
        db = self.get_db()
        doc_id = doc.get("_id") or doc.get("id")
        if doc_id and "_id" not in doc:
            doc["_id"] = doc_id

        if "_rev" in doc and not doc["_rev"]:
            del doc["_rev"]

        if doc.get("_id") and doc["_id"] in db:
            existing = db.get(doc["_id"])
            if existing and "_rev" in existing:
                doc["_rev"] = existing["_rev"]
            doc_id_saved, rev = db.save(doc)
            return {"id": doc_id_saved, "rev": rev, "ok": True}
        else:
            doc_id_saved, rev = db.save(doc)
            return {"id": doc_id_saved, "rev": rev, "ok": True}

    def find_by_selector(self, selector: dict[str, Any]) -> list[dict[str, Any]]:
        db = self.get_db()
        result = db.find({"selector": selector})
        return [dict(doc) for doc in result]


couchdb_client = CouchDBClient()
