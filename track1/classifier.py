"""Heuristic, zero-cost task classifier.

Runs locally (free) to route each prompt to one of the eight capability categories and
estimate difficulty, so the router can pick the cheapest capable handler.
"""

import re

CATEGORIES = (
    "math",
    "sentiment",
    "ner",
    "summarisation",
    "code_debug",
    "code_gen",
    "logic",
    "factual",
)

# Ordered (specific -> general): first strong match wins.
_KEYWORDS = [
    ("code_debug", (r"\bbug\b", r"\bfix\b", r"\bdebug\b", r"\berror\b", r"has a bug",
                    r"find and fix", r"corrected")),
    ("code_gen", (r"write a (python |javascript |)function", r"\bimplement\b",
                  r"write code", r"\bfunction that\b", r"\bwrite a program\b")),
    ("summaris", (r"\bsummar", r"\btl;dr\b", r"condense", r"in (exactly )?one sentence",
                  r"in \d+ words")),
    ("ner", (r"named entit", r"extract .*entit", r"\bentities\b", r"person, org")),
    ("sentiment", (r"\bsentiment\b", r"positive or negative", r"classify.*(review|tone|emotion)")),
    ("logic", (r"\beach own\b", r"who owns", r"puzzle", r"deduc", r"if .* then .*who",
               r"exactly one", r"constraint")),
    ("math", (r"\d+\s*%", r"how many", r"what is \d", r"calculate", r"\bsum\b",
              r"average", r"percent", r"\d+\s*[\+\-\*/x]\s*\d+", r"remain", r"total")),
]

_NORMALISE = {"summaris": "summarisation"}


def classify(prompt: str) -> str:
    """Return one of CATEGORIES for the given prompt (defaults to 'factual')."""
    p = prompt.lower()
    for cat, patterns in _KEYWORDS:
        for pat in patterns:
            if re.search(pat, p):
                return _NORMALISE.get(cat, cat)
    return "factual"


# Categories whose hard cases benefit most from an escalation to a stronger model.
HARD_CATEGORIES = {"math", "logic", "code_gen", "code_debug"}


def estimate_difficulty(prompt: str, category: str) -> str:
    """Coarse 'easy' | 'hard' estimate used to bias escalation decisions."""
    length = len(prompt.split())
    if category in HARD_CATEGORIES:
        return "hard"
    if length > 120:
        return "hard"
    return "easy"
