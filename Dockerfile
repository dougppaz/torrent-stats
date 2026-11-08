# Stage 1: Build dependencies
FROM python:3.15-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock README.md ./
COPY torrent_stats ./torrent_stats

# Install dependencies globally in the builder stage
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Stage 2: Runtime image
FROM python:3.15-slim AS runtime

WORKDIR /app

# Copy installed python packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.15/site-packages /usr/local/lib/python3.15/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code (excluding api specification folder)
COPY torrent_stats/ torrent_stats/

EXPOSE 8000

CMD ["uvicorn", "torrent_stats.main:app", "--host", "0.0.0.0", "--port", "8000"]
