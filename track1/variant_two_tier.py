#!/usr/bin/env python3
"""Variant C — Two-tier escalation router (token-minimising paid calls).

Strategy: local first (free). On escalation, try the *cheapest* allowed Fireworks model
first; only if that answer still looks invalid do we re-escalate to the *strongest* allowed
model. This spends the fewest paid tokens per escalated task while keeping a safety net for
hard prompts.

Assumes ALLOWED_MODELS[0] is a cheaper/smaller model and ALLOWED_MODELS[-1] a stronger one
(re-order the pick after seeing the launch-day list). Entrypoint: `python variant_two_tier.py`.
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


def _fw_call(fireworks: FireworksModel, prefer_strong: bool, system: str,
             prompt: str, budget: int):
    if not fireworks.available:
        return None
    model = fireworks.pick_model(prefer_strong)
    if not model:
        return None
    try:
        resp = fireworks.client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            max_tokens=budget,
            temperature=0.0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # pragma: no cover
        print(f"[fireworks] error ({model}): {exc}", flush=True)
        return None


def answer_task(task: dict, local: LocalModel, fireworks: FireworksModel) -> str:
    prompt = (task.get("prompt") or "").strip()
    if not prompt:
        return ""
    category = classifier.classify(prompt)

    det = handlers.try_handle(category, prompt)
    if det is not None:
        return det

    system = prompts.system_prompt(category)
    budget = prompts.max_tokens(category)

    # 1) Free local.
    local_ans = local.generate(system, prompt, max_tokens=budget)
    if prompts.looks_valid(category, local_ans):
        return local_ans

    # 2) Cheapest allowed model first.
    cheap = _fw_call(fireworks, False, system, prompt, budget)
    if prompts.looks_valid(category, cheap):
        return cheap

    # 3) Re-escalate to the strongest allowed model only if the cheap one also failed.
    strong = _fw_call(fireworks, True, system, prompt, budget)
    if strong:
        return strong

    return cheap or local_ans or ""


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
    print(f"[init] two-tier: local={'on' if local.available else 'off'} "
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

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"[done] {len(results)} tasks in {time.time() - start:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
