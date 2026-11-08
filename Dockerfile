FROM python:3.13-slim

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry

# Copy dependency specifications
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

# Copy source code
COPY torrent_stats/ torrent_stats/
COPY api/ api/

EXPOSE 8000

CMD ["uvicorn", "torrent_stats.main:app", "--host", "0.0.0.0", "--port", "8000"]
