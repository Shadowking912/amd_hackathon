#!/usr/bin/env python3
"""Variant A — Local-only router (zero Fireworks tokens).

Strategy: never call the paid API. Answer every task with deterministic handlers + the
free local model. If this clears the accuracy gate, it is unbeatable on token score
(flagged ZERO_API_CALLS) because total proxy tokens == 0.

Best when your bundled local model is strong enough to pass the gate on all 8 categories.
Swap this in as the container entrypoint: `python variant_local_only.py`.
"""

import json
import os
import sys
import time

import classifier
import handlers
import prompts
from models import LocalModel

INPUT_PATH = os.getenv("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/output/results.json")


def answer_task(task: dict, local: LocalModel) -> str:
    prompt = (task.get("prompt") or "").strip()
    if not prompt:
        return ""
    category = classifier.classify(prompt)

    # 1) Deterministic handler — 0 tokens.
    det = handlers.try_handle(category, prompt)
    if det is not None:
        return det

    # 2) Free local model. No escalation ever.
    ans = local.generate(prompts.system_prompt(category), prompt,
                         max_tokens=prompts.max_tokens(category))
    return ans or ""


def main() -> int:
    start = time.time()
    try:
        with open(INPUT_PATH, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except Exception as exc:
        print(f"[fatal] cannot read {INPUT_PATH}: {exc}", flush=True)
        return 1
    if not isinstance(tasks, list):
        print(f"[fatal] {INPUT_PATH} must be a JSON array", flush=True)
        return 1

    local = LocalModel()
    print(f"[init] local-only: local={'on' if local.available else 'off'}", flush=True)

    results = []
    for task in tasks:
        tid = task.get("task_id", "")
        try:
            ans = answer_task(task, local)
        except Exception as exc:
            print(f"[warn] task {tid} failed: {exc}", flush=True)
            ans = ""
        results.append({"task_id": tid, "answer": ans})

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"[done] {len(results)} tasks in {time.time() - start:.1f}s (0 API calls)",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
