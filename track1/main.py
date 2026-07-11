#!/usr/bin/env python3
"""AMD Hackathon Track 1 — Smart Router entrypoint.

Reads /input/tasks.json, answers each task via the cheapest capable path
(deterministic handler -> free local model -> paid Fireworks escalation), and writes
/output/results.json. Exits 0 on success.
"""

import json
import os
import sys
import time

import classifier
import handlers
import prompts
from models import FireworksModel, LocalModel

INPUT_PATH = os.getenv("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/output/results.json")


def answer_task(task: dict, local: LocalModel, fireworks: FireworksModel) -> str:
    """Resolve one task via the local-first, confidence-gated cascade."""
    prompt = (task.get("prompt") or "").strip()
    if not prompt:
        return ""

    category = classifier.classify(prompt)
    difficulty = classifier.estimate_difficulty(prompt, category)

    # 1) Deterministic handler — 0 tokens.
    det = handlers.try_handle(category, prompt)
    if det is not None:
        return det

    system = prompts.system_prompt(category)
    budget = prompts.max_tokens(category)

    # 2) Free local model first.
    local_ans = local.generate(system, prompt, max_tokens=budget)
    if prompts.looks_valid(category, local_ans):
        return local_ans

    # 3) Escalate to paid Fireworks only when local is unavailable/unreliable.
    prefer_strong = difficulty == "hard"
    fw_ans = fireworks.generate(system, prompt, prefer_strong=prefer_strong,
                                max_tokens=budget)
    if fw_ans:
        return fw_ans

    # 4) Last resort: return whatever local produced (better than empty for the gate).
    return local_ans or ""


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
    fireworks = FireworksModel()
    print(f"[init] local={'on' if local.available else 'off'} "
          f"fireworks={'on' if fireworks.available else 'off'} "
          f"models={fireworks.models}", flush=True)

    results = []
    for task in tasks:
        tid = task.get("task_id", "")
        try:
            ans = answer_task(task, local, fireworks)
        except Exception as exc:
            print(f"[warn] task {tid} failed: {exc}", flush=True)
            ans = ""
        results.append({"task_id": tid, "answer": ans})

    # Always write valid JSON before exiting.
    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    try:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False)
    except Exception as exc:
        print(f"[fatal] cannot write {OUTPUT_PATH}: {exc}", flush=True)
        return 1

    print(f"[done] {len(results)} tasks in {time.time() - start:.1f}s -> {OUTPUT_PATH}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
