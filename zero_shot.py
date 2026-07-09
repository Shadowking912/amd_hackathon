"""
Zero-shot stylistic video captioning — Technique A (style-conditioned prompt).

No training, no few-shot examples: a single style-conditioned instruction steers a
base vision-language model to caption a video in one of four styles.

Styles: formal, sarcastic, humorous_tech, humorous_nontech.

Setup:
    pip install openai opencv-python
    export FIREWORKS_API_KEY="fw_xxx"

Usage:
    python zero_shot_caption.py path/to/video.mp4                 # all four styles
    python zero_shot_caption.py path/to/video.mp4 sarcastic       # one style
"""

import argparse
import base64
import json
import os
import random
import sys
import time

import cv2
from openai import OpenAI

FIREWORKS_BASE_URL = os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1")
DEFAULT_MODEL = os.environ.get("ALLOWED_MODELS", "accounts/fireworks/models/qwen3-vl-8b-instruct").split(",")[0].strip()

# Per-style instruction + a sampling temperature tuned for that voice.
STYLES = {
    "formal": {
        "temperature": 0.3,
        "prompt": (
            "You are a professional video captioner. Watch the ordered frames and write "
            "ONE concise, neutral caption in complete sentences. No jokes, no opinions, "
            "no emojis. Describe only what is objectively visible."
        ),
    },
    "sarcastic": {
        "temperature": 0.6,
        "prompt": (
            "You are a dry, deadpan narrator. Caption the video in ONE sarcastic, ironic "
            "line. Mock the obvious, stay clever not mean, never use emojis or slurs."
        ),
    },
    "humorous_tech": {
        "temperature": 0.6,
        "prompt": (
            "You are a witty software engineer. Caption the video in ONE funny line using "
            "programming / DevOps / startup humor (bugs, prod, CI, standups). Keep it PG."
        ),
    },
    "humorous_non_tech": {
        "temperature": 0.6,
        "prompt": (
            "You are a stand-up comedian. Caption the video in ONE broadly funny, everyday "
            "line anyone can enjoy. No tech jargon. Keep it PG."
        ),
    },
}


def extract_frames(video_path, num_frames=8, fps=None, max_frames=16):
    """Sample JPEG frames from a video, base64-encoded.

    Two mutually exclusive modes:
      * fps=None (default): sample exactly `num_frames` frames spread evenly across
        the whole clip -> guaranteed full coverage regardless of length.
      * fps=<float>: sample at a constant rate (frames per second). The resulting
        count scales with duration and is capped at `max_frames`. As a reference,
        num_frames=24 corresponds to ~0.8 fps for a 30s clip and ~0.2 fps for a 2min
        clip, so fps in the 0.2-0.8 range covers the target 30s-2min videos.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(video_path)
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # In fps mode, convert a sampling rate into a concrete frame count for this clip.
    if fps is not None and total > 0:
        duration = total / src_fps
        num_frames = max(1, min(max_frames, int(round(duration * fps))))

    frames = []
    if total > 0:
        # Evenly spaced frame indices across the full duration.
        indices = [int(round(i * (total - 1) / max(1, num_frames - 1))) for i in range(num_frames)]
        for idx in sorted(set(indices)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok:
                ok2, buf = cv2.imencode(".jpg", frame)
                if ok2:
                    frames.append(base64.b64encode(buf).decode())
    else:
        # Fallback: frame count unknown -> read sequentially and subsample.
        raw, i = [], 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            raw.append(frame)
            i += 1
        for j in range(min(num_frames, len(raw))):
            idx = int(round(j * (len(raw) - 1) / max(1, num_frames - 1)))
            ok2, buf = cv2.imencode(".jpg", raw[idx])
            if ok2:
                frames.append(base64.b64encode(buf).decode())

    cap.release()
    if not frames:
        raise ValueError(f"No frames decoded from {video_path}")
    return frames


def caption_all_styles(frames_b64, styles, client, model=DEFAULT_MODEL, max_retries=3):
    """Ask the model for all requested styles in a single call with exponential backoff retries.

    Returns a dict mapping each style to its caption.
    Retries up to max_retries times on transient failures (timeout, rate limit, 5xx errors).
    """
    invalid = [s for s in styles if s not in STYLES]
    if invalid:
        raise ValueError(f"Unknown styles: {', '.join(invalid)}")

    style_lines = "\n".join(
        f"{i+1}. {style}: {STYLES[style]['prompt']}"
        for i, style in enumerate(styles)
    )

    prompt = (
        "You are a video captioning assistant. Watch the ordered frames and produce "
        f"exactly {len(styles)} captions, one for each style listed below.\n\n"
        f"{style_lines}\n\n"
        "Return ONLY a valid JSON object. Do not explain, do not think out loud, "
        "do not use markdown code blocks, do not include any text before or after the JSON. "
        "Each key must be exactly the style name, and each value must be the caption string.\n\n"
        "Required JSON format:\n"
        "{" + ", ".join(f'"{style}": "..."' for style in styles) + "}"
    )

    content = [{"type": "text", "text": prompt}]
    for f in frames_b64:
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{f}"}}
        )

    # Use the highest temperature among requested styles for a livelier mixed voice.
    temperature = max(STYLES[s]["temperature"] for s in styles)

    # Retry with exponential backoff
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            # Build API call kwargs
            api_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "temperature": temperature,
                "max_tokens": 1024,
                "timeout": 25,
                "response_format": {"type": "json_object"},
            }
            
            # Add model-specific parameters
            if "fireworks" in model.lower():
                api_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
            elif "gemini" in model.lower():
                api_kwargs["reasoning_effort"] = "low"
            
            resp = client.chat.completions.create(**api_kwargs)
            content_text = resp.choices[0].message.content
            if content_text is None:
                raise ValueError("Model returned empty content")
            raw = content_text.strip()
            break  # Success - exit retry loop
        except Exception as e:
            last_error = e
            is_retryable = (
                "timeout" in str(e).lower() or
                "429" in str(e) or  # Rate limit
                "500" in str(e) or  # Server error
                "503" in str(e)     # Service unavailable
            )
            if attempt < max_retries and is_retryable:
                wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff with jitter
                print(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}", file=sys.stderr)
                print(f"Retrying in {wait_time:.1f}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                # Non-retryable error or max retries reached
                raise

    # Try to extract JSON if the model wrapped it in markdown or reasoning text.
    if raw is None:
        raise ValueError(f"No response from model after {max_retries + 1} attempts")
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    # Find the first '{' and last '}' to isolate a JSON object inside extra text.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {raw}") from exc

    # Ensure every requested style is present.
    for style in styles:
        if style not in parsed:
            raise ValueError(f"Missing caption for style '{style}' in model output: {raw}")

    return {style: str(parsed[style]).strip() for style in styles}


def caption(frames_b64, style, client, model=DEFAULT_MODEL):
    """Zero-shot caption the frames in the given style (Technique A)."""
    return caption_all_styles(frames_b64, [style], client, model=model)[style]


def main():
    parser = argparse.ArgumentParser(description="Zero-shot stylistic video captioning (Technique A).")
    parser.add_argument("video", help="Path to the input video file.")
    parser.add_argument("style", nargs="?", choices=list(STYLES), help="Single style (default: all).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Fireworks model id.")
    parser.add_argument("--num-frames", type=int, default=16,
                        help="Frames sampled evenly across the whole clip (default 16, good for 30s-2min).")
    parser.add_argument("--fps", type=float, default=None,
                        help="Alternative to --num-frames: sample at a constant rate "
                             "(e.g. 0.5 = 1 frame every 2s). ~0.2-0.8 covers 30s-2min clips.")
    args = parser.parse_args()

    api_key = os.environ["FIREWORKS_API_KEY"]
    base_url = os.environ["FIREWORKS_BASE_URL"]

    frames = extract_frames(args.video, num_frames=args.num_frames, fps=args.fps)
    print(f"[{len(frames)} frames sampled from {args.video}]", file=sys.stderr)
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    styles = [args.style] if args.style else list(STYLES)
    for style in styles:
        print(f"{style:18s} -> {caption(frames, style, client, model=args.model)}")


if __name__ == "__main__":
    main()
