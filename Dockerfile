# Stage 1: Export requirements
FROM python:3.15-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry poetry-plugin-export

COPY pyproject.toml poetry.lock ./

RUN poetry export -f requirements.txt --output requirements.txt --only main

# Stage 2: Runtime image
FROM python:3.15-slim AS runtime

WORKDIR /app

COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code (excluding api specification folder)
COPY torrent_stats/ torrent_stats/

EXPOSE 8000

CMD ["uvicorn", "torrent_stats.main:app", "--host", "0.0.0.0", "--port", "8000"]
