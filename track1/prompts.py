"""Per-category prompts and local-answer verification.

System prompts are intentionally terse: on paid (Fireworks) calls, every input token counts
toward the score, so we avoid verbose role-play and redundant instructions.
"""

# Compact, category-specific system prompts. Output constraints keep response tokens low.
SYSTEM_PROMPTS = {
    "math": "Solve the problem. Think step by step internally, then output ONLY the final answer.",
    "sentiment": "Classify the sentiment (positive, negative, neutral, or mixed) and give a one-line reason.",
    "ner": "Extract named entities. Output each as 'text: TYPE' (PERSON, ORG, LOCATION, DATE). One per line.",
    "summarisation": "Summarise following the requested length/format exactly. Output only the summary.",
    "code_debug": "Identify the bug and output the corrected code. Be brief.",
    "code_gen": "Write correct, well-structured code for the spec. Output only the code.",
    "logic": "Solve the constraint puzzle. Verify all conditions hold. Output ONLY the answer.",
    "factual": "Answer accurately and concisely. Output only the answer.",
}

# Output budgets per category (fewer tokens = higher rank, but must not truncate answers).
MAX_TOKENS = {
    "math": 1024,
    "sentiment": 1024,
    "ner": 1024,
    "summarisation": 1024,
    "code_debug": 1024,
    "code_gen": 1024,
    "logic": 1024,
    "factual": 1024,
}


def system_prompt(category: str) -> str:
    return SYSTEM_PROMPTS.get(category, SYSTEM_PROMPTS["factual"])


def max_tokens(category: str) -> int:
    return MAX_TOKENS.get(category, 256)


def looks_valid(category: str, answer: str | None) -> bool:
    """Cheap local check on a local-model answer. False -> escalate to Fireworks.

    Catches obvious failures (empty, refusal, truncation) without a paid call.
    """
    if not answer or not answer.strip():
        return False
    a = answer.strip()
    low = a.lower()
    refusals = ("i cannot", "i can't", "as an ai", "i'm unable", "i am unable",
                "i don't know", "cannot help")
    if any(r in low for r in refusals):
        return False
    if len(a) < 2:
        return False
    if category in ("code_gen", "code_debug") and "def " not in a and "return" not in a \
            and "```" not in a:
        # Expect some code for code tasks.
        return False
    if category == "ner" and ":" not in a:
        return False
    return True
