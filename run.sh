#!/bin/bash
echo "HA Agent starting..."
export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"
cd /app
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
