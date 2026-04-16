#!/bin/bash
set -e

# Use PORT environment variable, default to 8000 if not set
PORT="${PORT:-8000}"

# Start the application
exec python -m uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
