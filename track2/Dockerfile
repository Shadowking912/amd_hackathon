FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg for Whisper audio extraction)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY zero_shot.py .
COPY entrypoint.py .

# Copy environment configuration bundled with the container.
# The judge injects credentials; use your own credentials inside the container.
COPY .env .

# Create input/output directories for mounted volumes.
RUN mkdir -p /input /output

# The container reads /input/tasks.json on startup and writes /output/results.json.
ENTRYPOINT ["python", "entrypoint.py"]
