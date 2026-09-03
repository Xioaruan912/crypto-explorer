#!/bin/sh
set -eu

mkdir -p /app/data
chown -R appuser:appuser /app/data

exec su -s /bin/sh appuser -c 'exec uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2 --no-server-header'
