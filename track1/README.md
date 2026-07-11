# Track 1 — General-Purpose AI Agent (Smart Router)

A practical guide for building the **AMD Developer Hackathon (ACT II) Track 1** agent: a
smart router that answers a wide variety of NL tasks across **eight capability categories**
while spending **as few Fireworks API tokens as possible**.

The core idea: **local models are free** (they count toward accuracy but **zero** toward the
token score). Only call a **Fireworks** model — routed through the proxy — when a task
genuinely needs it. Fewer proxy tokens = higher rank.

The eight capability categories (build for all of them):

| # | Category | What it covers |
|---|----------|----------------|
| 1 | **Factual knowledge** | Explaining concepts, definitions, how things work |
| 2 | **Mathematical reasoning** | Multi-step arithmetic, %, word problems, projections |
| 3 | **Sentiment classification** | Labelling sentiment + justifying it |
| 4 | **Text summarisation** | Condensing to a format / length constraint |
| 5 | **Named entity recognition** | Extract + label entities (person, org, location, date) |
| 6 | **Code debugging** | Find bugs in snippets, provide corrected code |
| 7 | **Logical / deductive reasoning** | Constraint puzzles where all conditions must hold |
| 8 | **Code generation** | Correct, well-structured functions from a spec |

---

## 1. How the task works

Your submission is a **Docker image** (`linux/amd64`, ≤10 GB compressed) that:

```
/input/tasks.json  ──►  router (classify → local or Fireworks)  ──►  /output/results.json
```

**Input** (`/input/tasks.json`):
```json
[
  { "task_id": "t1", "prompt": "Summarise the following text in one sentence: ..." },
  { "task_id": "t2", "prompt": "..." }
]
```

**Output** (`/output/results.json`) — must be valid JSON, each entry has `task_id` + `answer`:
```json
[
  { "task_id": "t1", "answer": "..." },
  { "task_id": "t2", "answer": "..." }
]
```

### Environment variables (injected by the harness — never hardcode)

```python
import os

api_key  = os.environ["FIREWORKS_API_KEY"]          # provided by harness — use THIS, not your own
base_url  = os.environ["FIREWORKS_BASE_URL"]         # route ALL Fireworks calls through this URL
models    = os.environ["ALLOWED_MODELS"].split(",")  # exact model IDs, published launch day
```

| Variable | Description |
|----------|-------------|
| `FIREWORKS_API_KEY` | Harness-provided key — use it, not your own |
| `FIREWORKS_BASE_URL` | Base URL for **all** Fireworks calls (OpenAI-compatible) |
| `ALLOWED_MODELS` | Comma-separated permitted model IDs, published on launch day |

> ⚠️ **All** Fireworks calls must go through `FIREWORKS_BASE_URL`, or they aren't recorded and
> you score **zero tokens** (which sounds good but means the call didn't count / may signal a
> bug). Only call models in `ALLOWED_MODELS` — anything else → `MODEL_VIOLATION`. Read the
> list at runtime; **do not hardcode model IDs**.

### Hard constraints

- **Grading VM: 4 GB RAM, 2 vCPU** — a local model must fit here. 2B–3B **4-bit quantized**
  is safe; a 7B 4-bit model fills the whole RAM budget, leaving no room for agent code.
- Exit **0** on success, non-zero on failure. Max runtime **10 min**. Start within **60 s**,
  per-request response **< 30 s**. English only.
- No hardcoding/caching answers — evaluation uses **unseen prompt variants**.
- Image must be publicly pullable and include a **`linux/amd64`** manifest.

---

## 2. Scoring model (what to optimise)

Two stages, in order:

1. **Accuracy gate** — an LLM-Judge scores each answer against expected intent. Below the
   threshold → **excluded from the leaderboard entirely** (`ACCURACY_GATE_FAILED`).
2. **Token efficiency** — among submissions that pass the gate, rank **ascending by total
   tokens recorded by the proxy**. Local tokens are free; only Fireworks proxy tokens count.

**Implication → a two-phase strategy:**
- **Phase 1 (must-do first): clear the gate.** Accuracy is a *gate*, not a gradient — get every
  category reliably above threshold before optimising anything.
- **Phase 2: drive proxy tokens down.** Move as many tasks as possible to free local models;
  for the tasks that still need Fireworks, trim system-prompt verbosity and output length.

> The task prompts are identical for every team — you only control **your system prompt
> (input tokens)** and **your model's response length (output tokens)**. Optimise routing and
> local-model coverage first; output-length tuning is a later-stage win.

---

## 3. Models

### Local models (free — the heart of your token score)

Must fit **4 GB RAM / 2 vCPU**, so use **2B–3B 4-bit quantized** (GGUF via `llama.cpp`/
`ollama`, or bitsandbytes/AWQ). Strong candidates by category:

| Local model (2–3B, 4-bit) | Good at |
|---------------------------|---------|
| **Qwen2.5-3B-Instruct** | All-rounder; solid math, NER, summarisation, sentiment |
| **Llama-3.2-3B-Instruct** | General NL, factual, summarisation |
| **Phi-3-mini (3.8B)** *tight fit* | Reasoning, math, code — quantize hard / test RAM headroom |
| **Qwen2.5-Coder-3B** | Code generation + debugging |
| **Gemma-2-2B-it** | Very small, fast; classification/sentiment/NER |

Plus **zero-model deterministic handlers** (no LLM at all) for the cheapest wins — see §4.A.

### Fireworks models (escalation only — every token counts)

Exact IDs come from `ALLOWED_MODELS` on launch day (do **not** hardcode). Route here **only**
for tasks your local models get wrong. Reserve the strongest allowed model for the hardest
categories (multi-step math, deductive puzzles, tricky code) and prefer smaller allowed models
when one clears the gate. Call via the OpenAI SDK against `FIREWORKS_BASE_URL`.

```python
from openai import OpenAI
client = OpenAI(api_key=os.environ["FIREWORKS_API_KEY"],
                base_url=os.environ["FIREWORKS_BASE_URL"])
```

---

## Techniques WITHOUT training (do these first)

No fine-tuning; pure routing + prompting. This is where most of the score is won.

### A. Deterministic / rule-based handlers (zero tokens)
Some tasks don't need an LLM at all. Detect them and answer in code — **0 tokens, instant**.
- **Math**: extract the arithmetic and evaluate with a safe expression parser / `sympy`.
- **NER**: spaCy (`en_core_web_sm`) locally for person/org/location/date.
- **Sentiment**: a small local classifier or lexicon for clear-cut cases.
- **Code debugging/generation**: run the snippet against generated asserts locally to verify.
- **Where it helps:** categories 2, 5, 3, and validation for 6/8 — all free.

### B. Task classification → route (the router core)
First step of the pipeline: classify each prompt into one of the 8 categories (+ a difficulty
estimate) and dispatch to the cheapest capable handler.
- **How:** a tiny **local** classifier (keyword/regex heuristics, or a 2B model with a compact
  prompt). Classification runs locally → **free**.
- **Route table:** category + difficulty → {deterministic handler | local model | Fireworks}.
- **Keep the classifier prompt tiny** — even though it's local, habits carry to paid calls.

### C. Local-first with confidence-gated escalation (cascade)
Always try a **local** model first. Escalate to Fireworks **only** when local output looks
unreliable. This is the single biggest token lever.
- **Confidence signals (local, free):** self-consistency across 2–3 local samples (agree →
  keep), a local verifier pass ("is this answer complete and correct? yes/no"), format/So
  schema checks, unit-test execution for code, re-deriving math.
- **Escalate** only failures → most tasks never touch the paid API.

### D. Self-verification & self-consistency (local)
Reduce escalations by catching local errors locally.
- **Math/logic:** sample 2–3 local answers, majority-vote; or verify by re-computing.
- **Code:** execute against asserts; only escalate if it fails.
- **Every task solved locally = free** and keeps you above the gate.

### E. Token-lean prompting (for the calls that do hit Fireworks)
Once routing is solid, trim the paid calls:
- Minimal system prompt — no verbose role-play or redundant instructions (**input tokens**).
- Constrain output: "answer only", "one sentence", "JSON only", stop sequences, `max_tokens`
  (**output tokens**).
- Ask for exactly the format the judge rewards — nothing extra.

### F. Few-shot / structured prompts — sparingly
Few-shot lifts accuracy but **adds input tokens on every call**. Use it on **local** models
freely; on Fireworks calls, only where it's the difference between passing/failing the gate.

---

## Techniques WITH training (optional, later-stage)

Only worth it once prompt+routing has plateaued. Goal: make the **free local** models handle
more categories so fewer tasks escalate. The grading VM never trains — you train **offline** and
**bundle the quantized adapter/model** in the image (respecting 4 GB RAM + 10 GB image limits).

### Method 1 — Fine-tune (LoRA) a small local model per weak category
SFT a 2–3B local model (e.g. Qwen2.5-3B) on the categories it currently fails, then quantize
to 4-bit and ship it. More local coverage → fewer paid escalations.
- **Data:** synthesize labelled examples for each category (see Method 3). Keep the base small
  enough to fit RAM after quantization.

### Method 2 — Distill from a large model into the local model
Use a strong model (offline, or an allowed Fireworks model during dev) to generate
high-quality answers for many category prompts, then LoRA-SFT the small local model on them.
Flagship-ish quality at local-model (free) cost during evaluation.

### Method 3 — Synthetic data + task-specific heads
Generate diverse synthetic tasks per category (varied phrasings, since eval uses unseen
variants) and train the local model / a lightweight classifier on them. Improves both the
**router's** category+difficulty accuracy and the **solver's** per-category accuracy.

> Constraints: the trained artifact must fit **4 GB RAM / 2 vCPU** at 4-bit and keep the image
> **≤ 10 GB compressed**. Validate RAM headroom leaves room for agent code.

---

## Recommended path

1. **Plumbing first.** Read `/input/tasks.json`, write valid `/output/results.json`, exit 0,
   fit 10-min / 60-s-start / 30-s-per-request. Validate on the practice tasks. A malformed
   output or crash scores zero regardless of answer quality.
2. **Clear the accuracy gate** with a capable **local** model + deterministic handlers (A) for
   every category. Nothing else matters until you're above threshold.
3. **Add the router** (B) + **local-first cascade** (C) + **self-verification** (D) so only hard
   tasks escalate to Fireworks.
4. **Trim paid calls** (E) — minimal system prompts, constrained output — then tune output
   length last.
5. **Optional:** LoRA / distillation (Methods 1–3) to push more categories fully local.

---

## Implementation & variants

The reference agent is modular: `classifier.py` (routing), `handlers.py` (deterministic),
`models.py` (`LocalModel` + `FireworksModel`), `prompts.py` (per-category prompts + local
validity checks). Pick **one** entrypoint below (set it in the `Dockerfile`):

| Entrypoint | Strategy | Best when |
|------------|----------|-----------|
| **`main.py`** | Balanced cascade: deterministic → local → single Fireworks escalation (strong model for hard categories). | Default; good accuracy/token trade-off. |
| **`variant_local_only.py`** | Never calls Fireworks — deterministic + local only (**0 proxy tokens**, `ZERO_API_CALLS`). | Your local model clears the gate on all 8 categories → unbeatable token score. |
| **`variant_self_consistency.py`** | Majority vote over multiple **free** local samples for math/logic; escalate only on disagreement. | Local model is decent but shaky on hard categories; buys accuracy with free tokens. |
| **`variant_two_tier.py`** | On escalation, try the **cheapest** allowed model first; re-escalate to the strongest only if it fails. | You want the fewest paid tokens per escalated task with a safety net. |

Recommended progression: start with `variant_local_only.py`; if it fails the gate on some
categories, move to `variant_self_consistency.py` or `main.py`; add `variant_two_tier.py`
once you know the relative cost/quality of the launch-day `ALLOWED_MODELS`.

---

## Troubleshooting (submission statuses)

| Status | Meaning & fix |
|--------|---------------|
| `PULL_ERROR` | Image not pullable / missing `linux/amd64` manifest. Build with `docker buildx build --platform linux/amd64 ... --push`. |
| `RUNTIME_ERROR` | Container exited non-zero. Reproduce locally, check agent logs. |
| `TIMEOUT` | Didn't finish in 10 min. Kill hangs, infinite loops, excessive retries; parallelise/limit escalations. |
| `OUTPUT_MISSING` | Exited cleanly but never wrote `/output/results.json`. Write it **before** exiting. |
| `INVALID_RESULTS_SCHEMA` | Each entry must be an object with both `task_id` and `answer`. |
| `MODEL_VIOLATION` | Called a model not in `ALLOWED_MODELS`. Read the env var at runtime; don't hardcode. |
| `IMAGE_TOO_LARGE` | Over 10 GB compressed. Trim layers/deps, use slim base + quantized model. |
| `ACCURACY_GATE_FAILED` | Answers below threshold — a quality issue, not infra. Improve local models / routing / prompts. |

> `flagged: ZERO_API_CALLS` is **not** a failure — it means a fully-local run made zero proxy
> calls (a valid, maximally token-efficient strategy).

## Build & submit

The `Makefile` wraps every step. Configurable variables: `IMAGE`, `TAG`, `PLATFORM`,
`ENTRYPOINT` (which router strategy), and `REPO`/`FILE` (which local model).

```bash
make model                                   # download models/local.gguf (~2 GB, REQUIRED)
make push IMAGE=<registry>/amd-router TAG=v1 # build linux/amd64 + push (what you submit)
```

Swap strategy or model at build time:
```bash
make push ENTRYPOINT=variant_local_only.py TAG=local-only
make model REPO=bartowski/Llama-3.2-3B-Instruct-GGUF FILE=Llama-3.2-3B-Instruct-Q4_K_M.gguf
```

Equivalent raw commands (no Make):
```bash
./download_model.sh                          # writes models/local.gguf (build fails without it)
docker buildx build --platform linux/amd64 --tag <registry>/amd-router:v1 --push .
```

Image must be **publicly pullable** at submission time. Submissions are rate-limited to
**10 per hour per team** — validate locally on the practice tasks before spending a slot.

> If you don't want a bundled local model, delete the two `COPY models/local.gguf` /
> `ENV LOCAL_MODEL_PATH` lines from the `Dockerfile` — the agent then routes everything to
> Fireworks (higher token cost).

## Local test harness

```bash
# Fast, no Docker — smoke-test the router directly:
make test                                    # or: make test ENTRYPOINT=variant_two_tier.py

# Full container run, mirroring the harness mounts (set the env vars first):
make run IMAGE=<registry>/amd-router TAG=v1 \
  FIREWORKS_API_KEY=... FIREWORKS_BASE_URL=... ALLOWED_MODELS=model-a,model-b
```

Raw equivalent of `make run`:
```bash
mkdir -p input output && cp practice_tasks.json input/tasks.json
docker run --rm \
  -e FIREWORKS_API_KEY="$FIREWORKS_API_KEY" \
  -e FIREWORKS_BASE_URL="$FIREWORKS_BASE_URL" \
  -e ALLOWED_MODELS="model-a,model-b" \
  -v "$PWD/input:/input" -v "$PWD/output:/output" \
  <registry>/amd-router:v1
python -m json.tool output/results.json      # must be valid JSON
```

## Key rules recap

- Local inference: counts toward **accuracy**, **zero** toward token score. Push as much here as possible.
- All Fireworks calls via `FIREWORKS_BASE_URL`; only `ALLOWED_MODELS`; read both from env.
- Fit 4 GB RAM / 2 vCPU; image ≤ 10 GB (`linux/amd64`); 10-min / 60-s / 30-s limits; English only.
- No hardcoded/cached answers — eval uses unseen variants.
