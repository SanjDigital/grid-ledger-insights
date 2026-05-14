#!/bin/bash
set -e

# Initialize database if needed
python scripts/init_db.py

# Create test mill if needed
python create_test_mill.py

# Start the application
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
