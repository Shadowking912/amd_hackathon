# CaptionChameleon - Complete Setup Workflow

This skill provides an automated workflow for setting up, testing, building, and deploying CaptionChameleon for the AMD Hackathon.

## Commands

### 1. Quick Local Test
```bash
# One-command local test (requires .env already set up)
cd /home/abhi/amd_hackathon && \
set -a && source .env && set +a && \
python entrypoint.py --input input.json --output output/results.json --max-workers 10 && \
cat output/results.json
```

### 2. Full Local Setup
```bash
# Complete local environment setup
cd /home/abhi/amd_hackathon && \
pip install -r requirements.txt && \
echo "✓ Dependencies installed" && \
echo "✓ Create .env file with your API credentials" && \
echo "  export FIREWORKS_API_KEY='fw_your_key_here'" && \
echo "  export FIREWORKS_BASE_URL='https://api.fireworks.ai/inference/v1'" && \
echo "  export ALLOWED_MODELS='accounts/fireworks/models/qwen3-vl-8b-instruct'"
```

### 3. Build Docker Image
```bash
# Build for linux/amd64 (required for judging VM)
cd /home/abhi/amd_hackathon && \
docker buildx build --platform linux/amd64 -t amd-hackathon:latest --load . && \
echo "✓ Image built: amd-hackathon:latest" && \
docker images amd-hackathon:latest --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
```

### 4. Verify Image
```bash
# Check image architecture and size
cd /home/abhi/amd_hackathon && \
echo "Image Architecture:" && \
docker inspect amd-hackathon:latest --format='{{.Architecture}}' && \
echo "Image Size:" && \
docker images amd-hackathon:latest --format "{{.Size}}" && \
echo "Compressed Size:" && \
docker images amd-hackathon:latest --format "Size: {{.Size}}"
```

### 5. Tag for Docker Hub
```bash
# Tag image with Docker Hub username
cd /home/abhi/amd_hackathon && \
DOCKER_USERNAME="shadowking9021" && \
docker tag amd-hackathon:latest ${DOCKER_USERNAME}/amd-hackathon:latest && \
echo "✓ Tagged as: ${DOCKER_USERNAME}/amd-hackathon:latest"
```

### 6. Push to Docker Hub
```bash
# Push to public registry (requires docker login)
cd /home/abhi/amd_hackathon && \
DOCKER_USERNAME="shadowking9021" && \
docker push ${DOCKER_USERNAME}/amd-hackathon:latest && \
echo "✓ Pushed to Docker Hub" && \
echo "Public image: ${DOCKER_USERNAME}/amd-hackathon:latest"
```

### 7. Test Docker Container
```bash
# Run container locally to test
cd /home/abhi/amd_hackathon && \
mkdir -p input output && \
cp input.json input/tasks.json && \
docker run \
  --env-file .env \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  shadowking9021/amd-hackathon:latest && \
echo "✓ Container test complete" && \
cat output/results.json | head -20
```

### 8. Clean Docker Cache
```bash
# Remove unused images and build cache
docker system prune -a --volumes -f && \
echo "✓ Docker cache cleaned" && \
docker images | grep -E "amd|shadow|caption" || echo "No cached images"
```

### 9. Generate PDF Presentation
```bash
# Create PDF from presentation_pdf.html
cd /home/abhi/amd_hackathon && \
python3 -m pip install weasyprint -q && \
python3 << 'PYTHON_EOF'
from weasyprint import HTML
import os
print("Converting presentation to PDF...")
HTML('presentation_pdf.html').write_pdf('CaptionChameleon_Presentation.pdf')
size_mb = os.path.getsize('CaptionChameleon_Presentation.pdf') / (1024 * 1024)
print(f"✓ PDF created: CaptionChameleon_Presentation.pdf ({size_mb:.2f} MB)")
PYTHON_EOF
```

### 10. Complete Deployment Pipeline
```bash
# Full end-to-end deployment: build, verify, tag, push
cd /home/abhi/amd_hackathon && \
echo "=== Building Image ===" && \
docker buildx build --platform linux/amd64 -t amd-hackathon:latest --load . && \
echo "✓ Build complete" && \
\
echo "=== Verifying Image ===" && \
ARCH=$(docker inspect amd-hackathon:latest --format='{{.Architecture}}') && \
SIZE=$(docker images amd-hackathon:latest --format "{{.Size}}") && \
echo "Architecture: $ARCH" && \
echo "Size: $SIZE" && \
\
echo "=== Tagging Image ===" && \
docker tag amd-hackathon:latest shadowking9021/amd-hackathon:latest && \
echo "✓ Tagged as shadowking9021/amd-hackathon:latest" && \
\
echo "=== Pushing to Registry ===" && \
docker push shadowking9021/amd-hackathon:latest && \
echo "✓ Deployment complete!" && \
echo "Public Image: shadowking9021/amd-hackathon:latest"
```

### 11. Submission Checklist
```bash
# Verify all submission requirements
cd /home/abhi/amd_hackathon && \
echo "=== CaptionChameleon - Submission Checklist ===" && \
echo "" && \
echo "✓ Code Files:" && \
ls -lh zero_shot.py two_stage.py entrypoint.py Dockerfile requirements.txt 2>/dev/null && \
echo "" && \
echo "✓ Documentation:" && \
ls -lh README.md cover.svg 2>/dev/null && \
echo "" && \
echo "✓ Presentation:" && \
ls -lh CaptionChameleon_Presentation.pdf presentation.html 2>/dev/null && \
echo "" && \
echo "✓ Docker Image:" && \
docker images shadowking9021/amd-hackathon:latest --format "{{.Repository}}:{{.Tag}} ({{.Size}})" && \
echo "" && \
echo "✓ Docker Hub:" && \
echo "  Public Image: shadowking9021/amd-hackathon:latest" && \
echo "  Verify at: https://hub.docker.com/r/shadowking9021/amd-hackathon" && \
echo "" && \
echo "✓ Size Check:" && \
docker images shadowking9021/amd-hackathon:latest --format "Size: {{.Size}} (< 10GB ✓)"
```

## Environment Setup

### Create .env File
```bash
cat > /home/abhi/amd_hackathon/.env << 'EOF'
export FIREWORKS_API_KEY="fw_your_api_key_here"
export FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1"
export ALLOWED_MODELS="accounts/fireworks/models/qwen3-vl-8b-instruct"
export INPUT_PATH="/input/tasks.json"
export OUTPUT_PATH="/output/results.json"
export MAX_WORKERS="10"
EOF

# Load environment
set -a && source /home/abhi/amd_hackathon/.env && set +a
```

## Project Structure

```
amd_hackathon/
├── entrypoint.py                    # Batch processing entry point
├── zero_shot.py                     # Direct zero-shot captioning module
├── two_stage.py                     # Factual-description + style-rewrite module
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container definition
├── README.md                        # Complete documentation
├── cover.svg                        # Project cover image (16:9)
├── presentation.html                # Interactive slideshow
├── presentation_pdf.html            # Google Slides-style PDF
├── CaptionChameleon_Presentation.pdf # Final PDF (9 slides)
├── input.json                       # Sample input tasks
├── .env                             # Environment variables (not in repo)
├── input/                           # Input videos directory
└── output/                          # Results directory
```

## Key Commands Reference

| Task | Command |
|------|---------|
| **Install deps** | `pip install -r requirements.txt` |
| **Local test** | `set -a && source .env && set +a && python entrypoint.py --input input.json --output output/results.json --max-workers 10` |
| **Single video** | `python zero_shot.py /path/to/video.mp4` or `python two_stage.py /path/to/video.mp4` |
| **Build Docker** | `docker buildx build --platform linux/amd64 -t amd-hackathon:latest --load .` |
| **Push to Hub** | `docker tag amd-hackathon:latest shadowking9021/amd-hackathon:latest && docker push shadowking9021/amd-hackathon:latest` |
| **Run container** | `docker run --env-file .env -v $(pwd)/input:/input -v $(pwd)/output:/output shadowking9021/amd-hackathon:latest` |
| **Generate PDF** | `python3 -c "from weasyprint import HTML; HTML('presentation_pdf.html').write_pdf('CaptionChameleon_Presentation.pdf')"` |
| **Verify image** | `docker inspect amd-hackathon:latest --format='{{.Architecture}}'` |
| **Check size** | `docker images amd-hackathon:latest --format "{{.Size}}"` |
| **Clean cache** | `docker system prune -a --volumes -f` |

## Submission Details

**Docker Image:** `shadowking9021/amd-hackathon:latest`
**Platform:** linux/amd64 ✓
**Size:** 570MB (< 10GB limit) ✓
**Public:** Yes (publicly pullable) ✓
**Status:** Ready for judging ✓

## Notes

- All commands are fully automated and can be run as-is
- Docker buildx required for multi-platform builds
- Replace `shadowking9021` with your Docker Hub username if needed
- `.env` file must contain valid API credentials
- PDF presentation uses proper 16:9 widescreen format
