#!/usr/bin/env sh
set -e

host="$1"; port="$2"; shift 2

# if a “--” separator is present, drop it
if [ "$1" = "--" ]; then
  shift
fi

# wait for Postgres
until pg_isready -h "$host" -p "$port"; do
  echo "Waiting for database at $host:$port..."
  sleep 2
done

# exec the remaining arguments (e.g. python ingest_*.py or uvicorn …)
exec "$@"
