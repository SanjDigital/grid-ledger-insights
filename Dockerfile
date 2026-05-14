FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy all source code
COPY backend/ backend/
COPY scripts/ scripts/
COPY data/ data/
COPY create_test_mill.py .

# Environment variables (these will be set by Railway)
ENV PYTHONUNBUFFERED=1

# Run FastAPI server with PORT environment variable support
ENTRYPOINT ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
