#!/usr/bin/env python
"""Start the FastAPI application with proper PORT handling."""
import os
import sys
import subprocess

print(f"[DEBUG] Environment variables: {dict(os.environ)}")
print(f"[DEBUG] Current working directory: {os.getcwd()}")

# Get PORT from environment variable, default to 8000
port = os.environ.get("PORT", "8000")

print(f"[INFO] Resolved port: {port}")
print(f"[INFO] PORT type: {type(port)}, value: '{port}'")

# Ensure port is a string of a valid integer
try:
    port_int = int(port)
    port = str(port_int)
    print(f"[INFO] Converted port to valid integer: {port}")
except ValueError:
    print(f"[ERROR] PORT value '{port}' is not a valid integer, using default 8000")
    port = "8000"

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
sys.stdout.flush()
os.execvp(cmd[0], cmd)
