#!/usr/bin/env bash
# Download a small (4B, 4-bit) GGUF local model into ./models for the router.
# Local inference is FREE toward the token score, so this is the highest-leverage step.
#
# Usage:
#   ./download_model.sh                 # default: Qwen3.5-4B Q4_K_M (~2.7 GB)
#   REPO=... FILE=... ./download_model.sh   # override with any single-file GGUF
#   HF_TOKEN=hf_xxx ./download_model.sh # auth for gated/private repos or higher rate limits
#
# Requires: python3 + huggingface_hub  (pip install -U huggingface_hub)
set -euo pipefail

# Reliable single-file GGUF (unsloth offers high-quality quantizations).
REPO="${REPO:-unsloth/Qwen3.5-4B-GGUF}"
FILE="${FILE:-Qwen3.5-4B-Q4_K_M.gguf}"
OUT_DIR="${OUT_DIR:-models}"
DEST="${OUT_DIR}/local.gguf"

# HF auth token: accept common env var names (do NOT hardcode a token in this file).
HF_TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-${HUGGINGFACE_TOKEN:-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}}}"

mkdir -p "${OUT_DIR}"

if ! python3 -c "import huggingface_hub" 2>/dev/null; then
  echo "Installing huggingface_hub..."
  pip install -U huggingface_hub
fi

if [ -n "${HF_TOKEN}" ]; then
  echo "Using Hugging Face token for authentication."
else
  echo "No HF token set (fine for public repos). Set HF_TOKEN=hf_xxx if the repo is gated."
fi

echo "Downloading ${REPO} :: ${FILE}"
HF_TOKEN="${HF_TOKEN}" python3 - "$REPO" "$FILE" "$OUT_DIR" "$DEST" <<'PY'
import os, shutil, sys
from huggingface_hub import hf_hub_download
repo, file, out_dir, dest = sys.argv[1:5]
token = os.environ.get("HF_TOKEN") or None
path = hf_hub_download(repo_id=repo, filename=file, local_dir=out_dir, token=token)
if path != dest:
    shutil.copyfile(path, dest)
print("Saved ->", dest)
PY

echo
echo "Done. The Dockerfile copies ${DEST} to /app/models/local.gguf and sets"
echo "LOCAL_MODEL_PATH accordingly. Now build:"
echo "  docker buildx build --platform linux/amd64 -t <registry>/amd-router:latest --push ."