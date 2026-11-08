from fastapi import FastAPI
from torrent_stats.config import settings

app = FastAPI(title=settings.app_name, version="1.0.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}
