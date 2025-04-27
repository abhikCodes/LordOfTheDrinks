FROM python:3.9-slim

WORKDIR /app

# install dependencies and pg_isready (from postgresql-client)
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# copy application code + helper script
COPY . .
RUN chmod +x wait-for-db.sh

# Only start the API server (ingestion handled by separate service)
CMD ["sh", "-c", "./wait-for-db.sh db 5432 -- uvicorn main:app --host 0.0.0.0 --port 8000"]