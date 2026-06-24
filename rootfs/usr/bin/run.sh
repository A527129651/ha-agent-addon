#!/usr/bin/with-contenv bashio
export ANTHROPIC_API_KEY="$(bashio::config 'anthropic_api_key')"
export HA_URL="http://supervisor/core"
export HA_TOKEN="${SUPERVISOR_TOKEN}"
bashio::log.info "Starting HA Agent..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
