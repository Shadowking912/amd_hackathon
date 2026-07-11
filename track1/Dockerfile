# AMD Hackathon Track 1 — Smart Router
# Judging VM is linux/amd64. On Apple Silicon build with:
#   docker buildx build --platform linux/amd64 -t <registry>/amd-router:latest --push .
FROM python:3.11-slim

# Build tools needed only if compiling llama-cpp-python from source; remove if you install a
# prebuilt wheel or drop local inference.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for faster dependency resolution and installation
RUN pip install uv --no-cache-dir

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt --system

COPY *.py ./

# Local model: run ./download_model.sh first to fetch models/local.gguf (a 4B, 4-bit GGUF).
# Local inference is free toward the token score. Keep image <= 10 GB and RAM under 4 GB.
COPY models/local.gguf /app/models/local.gguf
ENV LOCAL_MODEL_PATH=/app/models/local.gguf
ENV LOCAL_N_THREADS=2 LOCAL_N_CTX=2048

# Choose the router strategy at build time:
#   main.py (default) | variant_local_only.py | variant_self_consistency.py | variant_two_tier.py
ARG ENTRYPOINT_FILE=main.py
ENV ENTRYPOINT_FILE=${ENTRYPOINT_FILE}

ENTRYPOINT ["sh", "-c", "exec python \"$ENTRYPOINT_FILE\""]
