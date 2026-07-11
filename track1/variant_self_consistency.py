#!/usr/bin/env python3
"""Variant B — Self-consistency router (accuracy-first on hard categories).

Strategy: for hard, verifiable categories (math, logic) draw several *local* samples and
take a majority vote — free, and it catches local mistakes without a paid call. For code,
verify locally by execution before accepting. Escalate to Fireworks only when local
disagreement / verification fails.

Trades a few extra (free) local tokens for fewer paid escalations and a higher accuracy
gate pass rate. Swap in as entrypoint: `python variant_self_consistency.py`.
"""

import json
import os
import re
import sys
import time
from collections import Counter

import classifier
import handlers
import prompts
from models import FireworksModel, LocalModel

INPUT_PATH = os.getenv("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "/output/results.json")

SAMPLES = int(os.getenv("SC_SAMPLES", "3"))          # local votes for math/logic
VERIFIABLE = {"math", "logic"}


def _norm(ans: str) -> str:
    """Normalise for voting: last number for math, else lowercased trimmed text."""
    nums = re.findall(r"-?\d+\.?\d*", ans)
    return nums[-1] if nums else ans.strip().lower()


def _self_consistent_local(local: LocalModel, system: str, prompt: str, budget: int):
    """Return (answer, confident?) from a majority vote over local samples."""
    samples = []
    for i in range(SAMPLES):
        out = local.generate(system, prompt, max_tokens=budget,
                             temperature=0.0 if i == 0 else 0.7)
        if out:
            samples.append(out)
    if not samples:
        return None, False
    votes = Counter(_norm(s) for s in samples)
    top_key, top_n = votes.most_common(1)[0]
    winner = next(s for s in samples if _norm(s) == top_key)
    confident = top_n >= (len(samples) // 2 + 1) and len(samples) >= 2
    return winner, confident


def answer_task(task: dict, local: LocalModel, fireworks: FireworksModel) -> str:
    prompt = (task.get("prompt") or "").strip()
    if not prompt:
        return ""
    category = classifier.classify(prompt)
    difficulty = classifier.estimate_difficulty(prompt, category)

    det = handlers.try_handle(category, prompt)
    if det is not None:
        return det

    system = prompts.system_prompt(category)
    budget = prompts.max_tokens(category)
    ans = None

    if local.available and category in VERIFIABLE:
        ans, confident = _self_consistent_local(local, system, prompt, budget)
        if confident and prompts.looks_valid(category, ans):
            return ans
    else:
        ans = local.generate(system, prompt, max_tokens=budget)
        if prompts.looks_valid(category, ans):
            return ans

    fw = fireworks.generate(system, prompt, prefer_strong=(difficulty == "hard"),
                            max_tokens=budget)
    return fw or ans or ""


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
    print(f"[init] self-consistency({SAMPLES}): local={'on' if local.available else 'off'} "
          f"fireworks={'on' if fireworks.available else 'off'}", flush=True)

    results = []
    for task in tasks:
        tid = task.get("task_id", "")
        try:
            ans = answer_task(task, local, fireworks)
        except Exception as exc:
            print(f"[warn] task {tid} failed: {exc}", flush=True)
            ans = ""
        results.append({"task_id": tid, "answer": ans})

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"[done] {len(results)} tasks in {time.time() - start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
