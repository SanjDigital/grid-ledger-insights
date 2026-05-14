#!/bin/bash
set -e

# Start the application with proper PORT handling
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
