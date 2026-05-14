FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy backend code
COPY backend/ backend/
COPY scripts/ scripts/

# Environment variables (these will be set by Railway)
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run FastAPI app
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
