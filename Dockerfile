FROM python:3.11-slim

WORKDIR /app

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Install Python dependencies using uv
COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY zero_shot.py .
COPY two_stage.py .
COPY entrypoint.py .

# Copy environment configuration bundled with the container.
# The judge injects credentials; use your own credentials inside the container.
COPY .env .

# Create input/output directories for mounted volumes.
RUN mkdir -p /input /output

# The container reads /input/tasks.json on startup and writes /output/results.json.
ENTRYPOINT ["python", "entrypoint.py"]
