#!/usr/bin/env python
"""Start the FastAPI application with proper PORT handling."""
import os
import sys
import subprocess

# Get PORT from environment variable, default to 8000
port = os.environ.get("PORT", "8000")

print(f"[INFO] Starting FastAPI server on port {port}")

# Run uvicorn with the resolved port
cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "backend.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    port,
]

print(f"[INFO] Running command: {' '.join(cmd)}")
os.execvp(cmd[0], cmd)
