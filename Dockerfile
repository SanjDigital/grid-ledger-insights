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
COPY start.py .

# Make start script executable
RUN chmod +x start.py

# Environment variables (these will be set by Railway)
ENV PYTHONUNBUFFERED=1

# Run FastAPI through start.py which handles PORT environment variable
CMD ["python", "start.py"]
