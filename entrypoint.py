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
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
from openai import OpenAI

from zero_shot import STYLES, caption_all_styles, extract_frames

DEFAULT_INPUT_PATH = "/input/tasks.json"
DEFAULT_OUTPUT_PATH = "/output/results.json"


def download_video(url, dest_path, timeout=30):
    """Download a remote video to a local temporary path."""
    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=65536):
            f.write(chunk)


def process_one_task(task, client, model):
    """Download a video and return captions for all its requested styles."""
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
            download_video(video_url, tmp_path, timeout=30)
            video_path = tmp_path
        else:
            video_path = video_url

        frames = extract_frames(video_path, num_frames=8, max_frames=16)
        print(f"[{len(frames)} frames sampled for {task_id}]", file=sys.stderr)

        captions = caption_all_styles(frames, styles, client, model=model)
        for style, text in captions.items():
            print(f"  {task_id} {style}: {text}", file=sys.stderr)

        return {"task_id": task_id, "captions": captions}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def process_tasks(tasks, max_workers=10):
    """Process tasks in parallel with a thread pool."""
    api_key = os.environ["FIREWORKS_API_KEY"]
    base_url = os.environ["FIREWORKS_BASE_URL"]
    allowed_models = os.environ["ALLOWED_MODELS"].split(",")
    model = allowed_models[0].strip()

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_one_task, task, client, model): task
            for task in tasks
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    results.append(result)
            except Exception as exc:
                task_id = futures[future].get("task_id", "unknown")
                print(f"Task {task_id} failed: {exc}", file=sys.stderr)

    # Preserve input order.
    order = {task.get("task_id", "unknown"): i for i, task in enumerate(tasks)}
    results.sort(key=lambda r: order.get(r["task_id"], float("inf")))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch stylistic video captioning. Defaults match the Docker harness paths."
    )
    parser.add_argument(
        "--input",
        default=os.environ.get("INPUT_PATH", DEFAULT_INPUT_PATH),
        help=f"Path to tasks JSON (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("OUTPUT_PATH", DEFAULT_OUTPUT_PATH),
        help=f"Path to results JSON (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=int(os.environ.get("MAX_WORKERS", "10")),
        help="Number of videos to process in parallel (default: 10)",
    )
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    if not os.path.exists(input_path):
        sys.exit(f"Input file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    if not isinstance(tasks, list):
        sys.exit(f"Expected a JSON array in {input_path}")

    results = process_tasks(tasks, max_workers=args.max_workers)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Wrote {len(results)} result(s) to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
