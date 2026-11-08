from __future__ import annotations

from fastapi import FastAPI

from torrent_stats.api.routers.torrents import router as torrents_router
from torrent_stats.settings import app_settings

app = FastAPI(title=app_settings.app_name, version="1.0.0")

app.include_router(torrents_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
