# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY zero_shot.py .
COPY entrypoint.py .

# Create input/output directories for mounted volumes.
RUN mkdir -p /input /output

# Do NOT bundle environment secrets; the harness injects them at runtime.
# Required env vars: FIREWORKS_API_KEY, FIREWORKS_BASE_URL, ALLOWED_MODELS

# The container reads /input/tasks.json on startup and writes /output/results.json.
ENTRYPOINT ["python", "entrypoint.py"]
