#!/usr/bin/env bash
set -e

echo "==> Running Superset database migrations..."
/app/.venv/bin/superset db upgrade

echo "==> Setting up Admin user..."
/app/.venv/bin/superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME:-admin}" \
  --firstname "${SUPERSET_ADMIN_FIRST_NAME:-Admin}" \
  --lastname "${SUPERSET_ADMIN_LAST_NAME:-User}" \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@quant-platform.local}" \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true

echo "==> Initializing Superset roles and permissions..."
/app/.venv/bin/superset init

echo "==> Starting Superset web server..."
exec /app/docker/entrypoints/run-server.sh
