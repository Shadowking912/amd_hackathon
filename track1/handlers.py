"""Deterministic, zero-token handlers.

These answer certain tasks in pure Python with no LLM call at all — the cheapest possible
path (0 tokens, instant). Each handler returns a string answer, or None if it cannot
confidently handle the prompt (in which case the router falls back to a model).
"""

import ast
import operator
import re

# ---- Safe arithmetic evaluation ---------------------------------------------------------
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("non-numeric constant")
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def eval_arithmetic(expr: str):
    """Safely evaluate a pure arithmetic expression string, or return None."""
    try:
        tree = ast.parse(expr, mode="eval")
        return _safe_eval(tree.body)
    except Exception:
        return None


def _fmt(num) -> str:
    if isinstance(num, float) and num.is_integer():
        num = int(num)
    return str(num)


def try_math(prompt: str):
    """Handle only clean, single-expression arithmetic like 'What is 12 * (3 + 4)?'.

    Deliberately conservative: multi-step word problems are left to a model, because a
    wrong deterministic answer would fail the accuracy gate.
    """
    m = re.search(r"(?:what is|calculate|compute|evaluate)\s+([0-9\.\s\+\-\*/x%\(\)]+)",
                  prompt, re.IGNORECASE)
    if not m:
        return None
    expr = m.group(1).strip().rstrip("?.").replace("x", "*")
    if not re.search(r"[\+\-\*/%]", expr):
        return None
    result = eval_arithmetic(expr)
    if result is None:
        return None
    return _fmt(result)


def try_handle(category: str, prompt: str):
    """Dispatch to a deterministic handler by category. Returns answer str or None."""
    if category == "math":
        return try_math(prompt)
    # NER/sentiment could use spaCy/lexicons here if bundled; left to the local model by
    # default to stay dependency-light and above the accuracy gate.
    return None
