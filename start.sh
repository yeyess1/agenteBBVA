#!/bin/bash
set -e

# Use PORT environment variable (Render sets this, default is 10000)
PORT="${PORT:-10000}"

echo "Starting Uvicorn on port $PORT"

# Start the application
exec python -m uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
