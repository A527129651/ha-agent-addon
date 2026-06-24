#!/usr/bin/with-contenv bashio

# Read config from addon options
ANTHROPIC_KEY=$(bashio::config 'anthropic_api_key')
LOG_LEVEL=$(bashio::config 'log_level')

# HA Supervisor provides these automatically
HA_URL="http://supervisor/core"
HA_TOKEN="${SUPERVISOR_TOKEN}"

bashio::log.info "Starting HA Agent..."
bashio::log.info "Log level: ${LOG_LEVEL}"

export ANTHROPIC_API_KEY="${ANTHROPIC_KEY}"
export HA_URL="${HA_URL}"
export HA_TOKEN="${HA_TOKEN}"
export LOG_LEVEL="${LOG_LEVEL}"

exec uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level "${LOG_LEVEL}"
