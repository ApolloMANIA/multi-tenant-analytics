#!/bin/bash
set -e

echo "Waiting for database..."
sleep 5

superset db upgrade

superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@superset.local \
  --password admin \
  || true

superset init

echo "Superset ready — add DB: postgresql+psycopg2://superset_reader:superset_reader_secret@db:5432/analytics"

exec gunicorn \
  --bind "0.0.0.0:8088" \
  --workers 1 \
  --timeout 120 \
  --limit-request-line 0 \
  --limit-request-field_size 0 \
  "superset.app:create_app()"
