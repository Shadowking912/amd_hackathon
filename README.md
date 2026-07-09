# CaptionChameleon

**Adaptive Multi-Style Video Captioning at Scale**

## Short Description

CaptionChameleon dynamically generates video captions in multiple distinct styles using zero-shot learning. Process hundreds of videos in parallel and get professional-grade captions in formal, sarcastic, tech, and everyday humor styles—all without model fine-tuning.

## Long Description

**CaptionChameleon** is a high-performance, containerized video captioning system that adapts to any style. Like a chameleon changes colors, this system transforms the same video into four uniquely styled captions, each perfectly tailored for different audiences and contexts.

Powered by advanced vision-language models and zero-shot learning, CaptionChameleon processes videos by:
1. **Sampling frames**: Intelligently extracting 16 frames from each video for efficient processing
2. **Mode-selectable captioning**: Use `two_stage` to separate factual description from tone, or `zero_shot` for direct style-conditioned captions
3. **Parallel processing**: Using a thread pool executor to process multiple videos concurrently
4. **Multi-platform deployment**: Seamless support for both local execution and containerized Docker deployment

The four caption styles are carefully tuned for different audiences and contexts:
- **Formal**: Professional, objective descriptions suitable for technical documentation
- **Sarcastic**: Dry, witty commentary with ironic undertones
- **Humorous Tech**: Programming and DevOps humor for technical audiences
- **Humorous Non-Tech**: Everyday humor accessible to general audiences

CaptionChameleon enables fast, cost-effective video captioning at scale without the overhead of model training or fine-tuning, making it ideal for rapidly processing large video libraries with diverse audience needs.

## Features

- **Zero-shot learning**: No fine-tuning required; prompts separate factual video understanding from style rewriting
- **Batch processing**: Process multiple videos in parallel with configurable workers
- **Multi-style output**: Generate all 4 styles from one factual description per video
- **Docker support**: Containerized for easy deployment
- **Efficient frame sampling**: Intelligent JPEG frame extraction and encoding

## 📁 Submission Materials

All presentation and marketing materials are in the `submission/` folder:

```
submission/
├── CaptionChameleon_Presentation.pdf      # 9-slide professional presentation (PDF)
├── presentation_pdf.html                  # Interactive Google Slides-style presentation
├── CaptionChameleon_Intro.mp4            # 10-second video intro (2.1 MB)
└── cover.svg                              # Professional 16:9 cover image
```

**Use for:**
- Judge presentations
- Hackathon submissions
- Social media showcase
- Project documentation

## Quick Start

### Local Testing (60 seconds)

```bash
# 1. Clone and setup
git clone <repo>
cd amd_hackathon

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create environment file
cat > .env << 'EOF'
export FIREWORKS_API_KEY="fw_your_key_here"
export FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1"
export ALLOWED_MODELS="accounts/fireworks/models/qwen3p7-plus"
EOF

# 4. Run with test video
set -a && source .env && set +a
python entrypoint.py --input input.json --output output/results.json --max-workers 10

# 5. View results
cat output/results.json
```

### Docker Deployment (Production)

#### Available Image Tags

| Tag | Model | Frames | Score | Status |
|-----|-------|--------|-------|--------|
| `latest` | Kimi K2.6 | 8 | 76 | v1 - Original |
| `v2` | Qwen3.7-Plus | 8 | 82 | Previous |
| `v3` | Qwen3.7-Plus | 16 | 85 | Current |

#### Build and Run

```bash
# Option 1: Direct command (recommended)
docker buildx build --platform linux/amd64 -t shadowking9021/amd-hackathon:v4 --load .
docker push shadowking9021/amd-hackathon:v4

# Option 2: With variables (set in same shell)
export TAG="v4"
export REGISTRY="shadowking9021/amd-hackathon"
docker buildx build --platform linux/amd64 -t $REGISTRY:$TAG --load .
docker push $REGISTRY:$TAG

# Run container
docker run \
  --env-file .env \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  shadowking9021/amd-hackathon:v4

# Check output
cat output/results.json
```

**Current Submission Image:** `shadowking9021/amd-hackathon:v3`

### Generate Submission Materials

All presentation assets (video, PDF, cover, HTML) are generated via the utils folder:

```bash
# Generate all submission materials in one command
python3 utils/build_submission.py
```

This creates:
- ✓ `cover.svg` - Professional 16:9 cover image (3.8 KB)
- ✓ `CaptionChameleon_Intro.mp4` - 10-second video intro (2.1 MB)
- ✓ `CaptionChameleon_Presentation.pdf` - 9-slide presentation (25 KB)
- ✓ `presentation_pdf.html` - Interactive HTML presentation (14 KB)

See [utils/README.md](utils/README.md) for details on:
- Individual generators and customization
- Dependency requirements
- Build performance and output sizes
- CI/CD integration examples

### Complete Workflow

For all available commands and automated workflows, see [WORKFLOW.md](WORKFLOW.md):

- ✅ Complete deployment pipeline
- ✅ Docker image build & push
- ✅ Testing and verification
- ✅ PDF generation
- ✅ Submission checklist

Run the full deployment:
```bash
# Full end-to-end build, verify, tag, and push
bash -c "$(curl -s https://raw.githubusercontent.com/your-org/repo/main/scripts/deploy.sh)" || \
cat WORKFLOW.md | grep -A 20 "10. Complete Deployment Pipeline"
```

## Prerequisites

### Local Development
- Python 3.11+
- OpenCV (cv2)
- OpenAI Python SDK
- Requests library
- API credentials for Fireworks (or compatible OpenAI-compatible API)

### Docker
- Docker 20.10+
- BuildX plugin (for multi-platform builds)

## Setup

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Configuration
export FIREWORKS_API_KEY="fw_your_api_key_here"
export FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1"
export ALLOWED_MODELS="accounts/fireworks/models/qwen3p7-plus"

# Paths
export INPUT_PATH="/input/tasks.json"
export OUTPUT_PATH="/output/results.json"

# Processing
export MAX_WORKERS="10"
export NUM_FRAMES="8"           # Frames to sample per video (default: 8)
export MAX_FRAMES="16"          # Max frames in FPS mode (default: 16)
export FRAME_FPS=""             # Frame rate (fps). Leave empty for adaptive mode
export CAPTION_MODE="two_stage" # two_stage or zero_shot (default: two_stage)
```

**Frame Extraction Settings:**
- **NUM_FRAMES**: Number of frames to extract from each video (default: 8)
- **MAX_FRAMES**: Maximum frames when using FPS mode (default: 16)
- **FRAME_FPS**: Sampling rate in frames-per-second. Leave empty for adaptive mode (intelligently spaced frames)

**Caption Modes:**
- **two_stage**: VLM first writes a factual description, then a text rewrite call produces all requested styles.
- **zero_shot**: VLM directly writes requested styles from frames in one style-conditioned call.

## Running Locally

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Input

Create an `input.json` file with the following format:

```json
[
  {
    "task_id": "v1",
    "video_url": "https://storage.example.com/clip1.mp4",
    "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    "mode": "two_stage"
  },
  {
    "task_id": "v2",
    "video_url": "https://storage.example.com/clip2.mp4",
    "styles": ["formal", "sarcastic"],
    "mode": "zero_shot"
  }
]
```

Alternatively, use local file paths:

```json
[
  {
    "task_id": "local1",
    "video_url": "/path/to/video.mp4",
    "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    "mode": "two_stage"
  }
]
```

### 3. Run the Batch Processor

```bash
# Load environment and run
set -a && source .env && set +a
python entrypoint.py --input input.json --output output/results.json --max-workers 10
```

Or with explicit arguments:

```bash
python entrypoint.py \
  --input input.json \
  --output output/results.json \
  --max-workers 10 \
  --mode two_stage
```

### 4. View Results

Results are written to `output/results.json`:

```json
[
  {
    "task_id": "v1",
    "captions": {
      "formal": "A person wearing formal attire is seated at a desk...",
      "sarcastic": "Oh wow, someone sitting at a desk... groundbreaking.",
      "humorous_tech": "Principal engineer debugging prod on Friday at 5pm.",
      "humorous_non_tech": "This is what productivity looks like, apparently."
    }
  }
]
```

### Single Video (CLI)

For quick testing with a single video:

```bash
python zero_shot.py /path/to/video.mp4           # direct zero-shot, all 4 styles
python zero_shot.py /path/to/video.mp4 formal    # direct zero-shot, one style
python two_stage.py /path/to/video.mp4           # two-stage, all 4 styles
python two_stage.py /path/to/video.mp4 formal    # two-stage, one style
```

## Building Docker Image

### 1. Build for linux/amd64

Build using `docker buildx` to ensure proper linux/amd64 manifest for the judging VM:

```bash
cd /home/abhi/amd_hackathon
docker buildx build --platform linux/amd64 -t amd-hackathon:latest --load .
```

**Important:** The judging environment runs `linux/amd64`. Using `buildx` with `--platform linux/amd64` ensures your image has the correct manifest and will successfully pull on the judging VM.

For local testing only (may not work on judging VM):
```bash
docker build -t amd-hackathon:latest .
```

### 2. Verify Image Architecture

```bash
docker inspect amd-hackathon:latest | grep -i architecture
```

Expected output: `linux/amd64`

### 3. Push to Docker Hub (Public Registry)

The image is already available publicly at Docker Hub. To push updates or rebuild:

```bash
# Tag the image with your Docker Hub username
docker tag amd-hackathon:latest shadowking9021/amd-hackathon:latest

# Push to public registry
docker push shadowking9021/amd-hackathon:latest
```

**Public Image Reference:**
```
shadowking9021/amd-hackathon:latest
```

Anyone can pull this image without authentication:
```bash
docker pull shadowking9021/amd-hackathon:latest
```

**For Judging Submission:** Use `shadowking9021/amd-hackathon:latest` as the container image reference.

### 4. Prepare Input Volume

```bash
mkdir -p input output
# Place tasks.json in the input directory
cp input.json input/tasks.json
```

### 5. Run Container

```bash
docker run \
  --env-file .env \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  shadowking9021/amd-hackathon:latest
```

Or with explicit arguments:

```bash
docker run \
  --env-file .env \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  shadowking9021/amd-hackathon:latest \
  --input /input/tasks.json \
  --output /output/results.json \
  --max-workers 10 \
  --mode two_stage
```

### 6. Verify Output

```bash
cat output/results.json
```

## Performance Optimization

### Local Execution
- **Frame count**: 16 frames per video (v3 - enhanced quality for better captions)
- **Parallel workers**: 10 (adjustable via `--max-workers`)
- **Two-stage API calls**: One VLM call produces factual description, one rewrite call produces all requested styles
- **Thinking disabled**: Extended reasoning disabled for faster responses (Kimi 2.6+)

### To Adjust Performance

**Increase parallelism** (for more videos):
```bash
python entrypoint.py --input input.json --output output/results.json --max-workers 20
```

**Modify frame count** (in `zero_shot.py`):
```python
frames = extract_frames(video_path, num_frames=6)  # reduce from 8 to 6
```

**Reduce output tokens** (in `zero_shot.py` or `two_stage.py`):
```python
max_tokens=256,  # reduce from 512
```

## Architecture

### Entrypoint (`entrypoint.py`)
- Reads batch of tasks from JSON input
- Downloads videos (HTTP/HTTPS) or uses local paths
- Manages thread pool for parallel processing
- Aggregates results and writes to JSON output

### Zero-Shot Captioner (`zero_shot.py`)
- Extracts frames from video using OpenCV
- Encodes frames as base64 JPEG
- Calls vision-language model with direct style-conditioned prompts
- Parses JSON response from model

### Two-Stage Captioner (`two_stage.py`)
- Produces a factual VLM description from frames
- Rewrites that factual description into requested styles
- Parses JSON response from model

## Troubleshooting

### API Key Issues
```
Error: FIREWORKS_API_KEY environment variable not set
```
Ensure `.env` is properly sourced:
```bash
set -a && source .env && set +a
```

### Missing Frames
```
ValueError: No frames decoded from video_path
```
Check that the video file is accessible and in a supported format (MP4, AVI, MOV).

### JSON Parsing Errors
```
ValueError: Model did not return valid JSON
```
The model may be returning reasoning or markdown. This is handled automatically, but verify the API key and model selection.

### Docker Build Fails
Ensure Docker daemon is running:
```bash
docker ps  # test connectivity
```

## API Reference

### Input Format (`tasks.json`)

```json
{
  "task_id": "unique_identifier",
  "video_url": "https://... or /local/path/...",
  "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
  "mode": "two_stage"
}
```

### Output Format (`results.json`)

```json
{
  "task_id": "unique_identifier",
  "captions": {
    "formal": "...",
    "sarcastic": "...",
    "humorous_tech": "...",
    "humorous_non_tech": "..."
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FIREWORKS_API_KEY` | Yes | - | API key for vision-language model |
| `FIREWORKS_BASE_URL` | No | `https://api.fireworks.ai/inference/v1` | API endpoint |
| `ALLOWED_MODELS` | No | `accounts/fireworks/models/qwen3p7-plus` | Model identifier |
| `INPUT_PATH` | No | `/input/tasks.json` | Path to input tasks (local or Docker) |
| `OUTPUT_PATH` | No | `/output/results.json` | Path to output results (local or Docker) |
| `MAX_WORKERS` | No | `10` | Number of parallel workers |
| `NUM_FRAMES` | No | `8` | Frames to extract per video |
| `MAX_FRAMES` | No | `16` | Max frames in FPS mode |
| `FRAME_FPS` | No | `` (empty) | Sampling rate in fps. Empty = adaptive mode |
| `CAPTION_MODE` | No | `two_stage` | Captioning mode: `two_stage` or `zero_shot` |

## Performance Metrics

**Typical execution on 3 videos (16 frames each):**
- Frame extraction: ~2s per video
- API calls: ~5-8s per video (depends on API latency)
- Total with 10 workers: ~14-15s for 3 videos

## License

Proprietary - AMD Hackathon

## Support

For issues or questions, refer to the source code documentation in `zero_shot.py`, `two_stage.py`, and `entrypoint.py`.
