from __future__ import annotations

import logging

from fastapi import FastAPI

from torrent_stats.api.routers.torrents import router as torrents_router
from torrent_stats.api.routers.worker import router as worker_router
from torrent_stats.settings import app_settings

logging.basicConfig(
    level=getattr(logging, app_settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title=app_settings.app_name, version="1.0.0")

app.include_router(torrents_router)
app.include_router(worker_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
