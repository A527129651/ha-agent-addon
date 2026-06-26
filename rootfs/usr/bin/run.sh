#!/bin/bash

ANTHROPIC_KEY="${ANTHROPIC_API_KEY}"
LOG_LEVEL="${LOG_LEVEL:-info}"

export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"

exec python3 -m uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level "$LOG_LEVEL"
