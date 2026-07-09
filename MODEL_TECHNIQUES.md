# Video Captioning Model Techniques: Comparison & Analysis

## Executive Summary

This document compares different approaches to video captioning, including the technique used in **CaptionChameleon** (current implementation).

---

## Technique Comparison Table

| **Technique** | **Model** | **Training Required** | **Cost per Video** | **Score** | **Frames** | **Docker Tag** |
|---|---|---|---|---|---|---|
| **Zero-Shot Style-Conditioned Prompting** ⭐ | Qwen3.7-Plus | None | $1.17 | **85** | 16 | `v3` |
| Zero-Shot Style-Conditioned Prompting | Qwen3.7-Plus | None | $0.47 | 82 | 8 | `v2` |
| Zero-Shot Style-Conditioned Prompting | Kimi K2.6 | None | $2 | 76 | 8 | `latest` |

---

## Current Implementation: CaptionChameleon

### ✅ Model Configuration
- **Vision-Language Model:** Qwen3.7-Plus (Fireworks AI)
- **Provider:** accounts/fireworks/models/qwen3p7-plus
- **Extended Thinking:** Disabled (`extra_body={"thinking": {"type": "disabled"}}`)
- **Technique:** Zero-Shot Style-Conditioned Prompting
- **Frame Sampling:** 16 frames (intelligent temporal spacing)
- **Batch Processing:** 4 styles in 1 API call
- **Parallelization:** ThreadPoolExecutor (10 workers)
- **Score:** 85/100

### 🎯 How It Works
```
Input Video
    ↓
Frame Extraction (16 frames, evenly spaced)
    ↓
Encode to Base64 (JPEG)
    ↓
Send to Qwen3.7-Plus with Style-Conditioned Prompt
    ↓
Receive 4 Captions (formal, sarcastic, humorous_tech, humorous_non_tech)
    ↓
Exponential Backoff Retry (3 retries with jitter)
    ↓
Return Results
```

### ⚙️ Style Configuration
Each style has a temperature-tuned prompt:

| Style | Temperature | Tone | Use Case |
|-------|---|---|---|
| **formal** | 0.3 (low) | Professional, neutral | News, documentation |
| **sarcastic** | 0.9 (high) | Ironic, witty | Entertainment, commentary |
| **humorous_tech** | 0.9 (high) | Tech jokes, puns | Developer content |
| **humorous_non_tech** | 0.7 (medium) | General humor | Casual content |

---

## Model Performance

### Current Implementation - Qwen3.7-Plus (v3)
| Metric | Value |
|--------|-------|
| **Score** | 85/100 |
| **Latency** | 3-6 seconds per video |
| **Cost per Video** | $0.88 (4 styles) |
| **Frames** | 16 (intelligently sampled) |
| **API Calls** | 1 per video (all 4 styles batched) |
| **Parallel Workers** | 10 (configurable) |
| **Retries** | 3 with exponential backoff + jitter |

---

## Key Implementation Details

- **No training data required** — Uses pre-trained Qwen3.7-Plus model (v3 with 16 frames)
- **Single API call per video** — All 4 styles generated in batch
- **Parallel processing** — 10 workers handle concurrent videos
- **Retry logic** — Exponential backoff for transient failures
- **Frame sampling** — 16 intelligently distributed frames per video
- **Style conditioning** — Temperature-tuned prompts per style (0.3-0.9)
