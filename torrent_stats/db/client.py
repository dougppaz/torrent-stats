from __future__ import annotations

from typing import Any

import httpx
from torrent_stats.settings import couchdb_settings


class CouchDBClient:
    def __init__(self) -> None:
        self.base_url = couchdb_settings.couchdb_url.rstrip("/")
        self.db_name = couchdb_settings.couchdb_db_name
        self.url = f"{self.base_url}/{self.db_name}"

    async def ensure_db_exists(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url)
            if response.status_code == 404:
                await client.put(self.url)

    async def get_doc(self, doc_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.url}/{doc_id}")
            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                return data
            return None

    async def save_doc(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc_id = doc.get("_id") or doc.get("id")
        if doc_id and "_id" not in doc:
            doc["_id"] = doc_id

        async with httpx.AsyncClient() as client:
            if doc.get("_id"):
                existing = await self.get_doc(doc["_id"])
                if existing and "_rev" in existing:
                    doc["_rev"] = existing["_rev"]
                response = await client.put(f"{self.url}/{doc['_id']}", json=doc)
            else:
                response = await client.post(self.url, json=doc)
            response.raise_for_status()
            res_data: dict[str, Any] = response.json()
            return res_data

    async def find_by_selector(self, selector: dict[str, Any]) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/_find", json={"selector": selector}
            )
            if response.status_code == 200:
                res_json: dict[str, Any] = response.json()
                docs: list[dict[str, Any]] = res_json.get("docs", [])
                return docs
            return []


couchdb_client = CouchDBClient()
