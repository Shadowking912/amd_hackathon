"""
Docker entrypoint: read a batch of tasks from /input/tasks.json, caption each
video in every requested style, and write /output/results.json.

Expected input format (/input/tasks.json):
[
  {
    "task_id": "v1",
    "video_url": "https://storage.example.com/clips/clip1.mp4",
    "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
  }
]

Output format (/output/results.json):
[
  {
    "task_id": "v1",
    "captions": {
      "formal": "...",
      "sarcastic": "...",
      "humorous_tech": "...",
      "humorous_non_tech": "..."
    }
  }
]
"""

import argparse
import json
import os
import random
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file BEFORE importing zero_shot (which reads env vars at module level)
load_dotenv()

from zero_shot import STYLES, caption_all_styles, extract_frames

# Frame extraction settings
NUM_FRAMES = int(os.environ.get("NUM_FRAMES", "8"))
MAX_FRAMES = int(os.environ.get("MAX_FRAMES", "16"))
_frame_fps = os.environ.get("FRAME_FPS", "").strip()
FRAME_FPS = float(_frame_fps) if _frame_fps else None  # None = adaptive mode, otherwise float fps

DEFAULT_INPUT_PATH = "/input/tasks.json"
DEFAULT_OUTPUT_PATH = "/output/results.json"
TASK_TIMEOUT = 30  # Timeout per task in seconds


def download_video(url, dest_path, timeout=30, max_retries=3):
    """Download a remote video to a local temporary path with exponential backoff retries."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    f.write(chunk)
            return  # Success
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
                print(f"Download failed (attempt {attempt + 1}/{max_retries + 1}): {e}", file=sys.stderr)
                print(f"Retrying in {wait_time:.1f}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise


def process_one_task(task, client, model, max_retries=3):
    """Download a video and return captions for all its requested styles with retries."""
    task_id = task.get("task_id", "unknown")
    video_url = task.get("video_url")
    styles = task.get("styles", list(STYLES))

    print(f"Processing task {task_id}: {video_url}", file=sys.stderr)

    if not video_url:
        print(f"Skipping task {task_id}: missing video_url", file=sys.stderr)
        return None

    invalid = [s for s in styles if s not in STYLES]
    if invalid:
        print(f"Skipping task {task_id}: unknown styles {invalid}", file=sys.stderr)
        return None

    parsed = urlparse(video_url)
    suffix = os.path.splitext(parsed.path)[1] or ".mp4"
    tmp_path = tempfile.mktemp(suffix=suffix)

    try:
        if parsed.scheme in ("http", "https"):
            download_video(video_url, tmp_path, timeout=30, max_retries=max_retries)
            video_path = tmp_path
        else:
            video_path = video_url

        frames = extract_frames(video_path, num_frames=NUM_FRAMES, fps=FRAME_FPS, max_frames=MAX_FRAMES)
        print(f"[{len(frames)} frames sampled for {task_id}]", file=sys.stderr)

        captions = caption_all_styles(frames, styles, client, model=model, max_retries=max_retries)
        for style, text in captions.items():
            print(f"  {task_id} {style}: {text}", file=sys.stderr)

        return {"task_id": task_id, "captions": captions}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def process_tasks(tasks, max_workers=10):
    """Process tasks in parallel with a thread pool."""
    # Check for required environment variables
    required_vars = ["FIREWORKS_API_KEY", "FIREWORKS_BASE_URL", "ALLOWED_MODELS"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Set these before running the container."
        )
    
    api_key = os.environ["FIREWORKS_API_KEY"]
    base_url = os.environ["FIREWORKS_BASE_URL"]
    allowed_models = os.environ["ALLOWED_MODELS"].split(",")
    model = allowed_models[0].strip()

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    results = []
    failed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_one_task, task, client, model): task
            for task in tasks
        }
        for future in as_completed(futures):
            task_id = futures[future].get("task_id", "unknown")
            try:
                result = future.result(timeout=TASK_TIMEOUT)
                if result is not None:
                    results.append(result)
                else:
                    failed += 1
            except TimeoutError:
                # Task exceeded timeout - return empty captions for all 4 styles
                print(f"Task {task_id} timed out after {TASK_TIMEOUT}s - returning empty captions", file=sys.stderr)
                styles = futures[future].get("styles", list(STYLES))
                empty_captions = {style: "" for style in styles}
                results.append({"task_id": task_id, "captions": empty_captions})
                failed += 1
            except Exception as exc:
                print(f"Task {task_id} failed: {exc}", file=sys.stderr)
                failed += 1

    # Preserve input order.
    order = {task.get("task_id", "unknown"): i for i, task in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r["task_id"], float("inf")))
    return results, failed


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Batch stylistic video captioning. Defaults match the Docker harness paths.",
            add_help=True,
        )
        # Accept all known argument name variants used by different judge platforms
        parser.add_argument("--input", default=None, help="Path to tasks JSON")
        parser.add_argument("--tasks-path", "--tasks_path", dest="tasks_path", default=None, help="Path to tasks JSON")
        parser.add_argument("--output", default=None, help="Path to results JSON")
        parser.add_argument("--results-path", "--results_path", dest="results_path", default=None, help="Path to results JSON")
        parser.add_argument(
            "--max-workers",
            type=int,
            default=int(os.environ.get("MAX_WORKERS", "10")),
            help="Number of videos to process in parallel (default: 10)",
        )
        args, _ = parser.parse_known_args()  # ignore unknown args instead of crashing

        # Resolve input path: --tasks-path > --input > env var > fixed default
        input_path = (
            args.tasks_path
            or args.input
            or os.environ.get("INPUT_PATH")
            or DEFAULT_INPUT_PATH
        )
        # Resolve output path: --results-path > --output > env var > fixed default
        output_path = (
            args.results_path
            or args.output
            or os.environ.get("OUTPUT_PATH")
            or DEFAULT_OUTPUT_PATH
        )

        if not os.path.exists(input_path):
            print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        with open(input_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        if not isinstance(tasks, list):
            print(f"ERROR: Expected a JSON array in {input_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Processing {len(tasks)} task(s)...", file=sys.stderr)
        results, failed = process_tasks(tasks, max_workers=args.max_workers)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"Wrote {len(results)} result(s) to {output_path}", file=sys.stderr)
        if failed:
            print(f"ERROR: {failed} task(s) failed", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
