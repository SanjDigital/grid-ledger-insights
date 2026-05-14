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
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Environment variables (these will be set by Railway)
ENV PYTHONUNBUFFERED=1

# Use bash to execute the entrypoint script with proper environment variable expansion
ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
