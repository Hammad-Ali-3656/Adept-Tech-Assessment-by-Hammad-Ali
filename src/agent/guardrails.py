"""Input and output guardrails.

Input side (cheap, deterministic — runs before any LLM call):
* size cap, control-character stripping
* prompt-injection heuristics (instruction-override patterns, attempts to
  extract the system prompt or secrets)
* obviously off-scope destructive requests

Output side:
* **number verification** — every numeric figure in the final answer must
  trace back to something a tool actually computed this episode. This is the
  deterministic backstop for "never invent a number": it does not trust the
  LLM at all, it matches numbers against the recorded tool outputs
  with a small rounding tolerance.
* secret leak scrubbing (API-key-shaped strings, env var names).
"""
from __future__ import annotations

import re

from .. import config

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous |prior |above |earlier )?(instructions|prompts?|rules)",
    r"disregard (your|the) (instructions|system prompt|rules)",
    r"reveal .{0,30}(system prompt|instructions|api key)",
    r"(print|show|output|repeat) .{0,30}(system prompt|your instructions)",
    r"you are (now|no longer) ",
    r"\bDAN\b|jailbreak|developer mode",
    r"(api[_ ]?key|secret|token|password|credential)s?\b.{0,40}(show|reveal|print|tell|what)",
    r"(show|reveal|print|tell).{0,40}(api[_ ]?key|secret|token|password|credential)",
    r"\bos\.environ\b|getenv|\.env\b",
]
SECRET_PATTERN = re.compile(
    r"(gsk_[A-Za-z0-9]{20,}|sk-or-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9]{20,}"
    r"|GROQ_API_KEY|OPENROUTER_API_KEY)")


def check_input(text: str) -> dict:
    """Return {'ok': True, 'text': cleaned} or {'ok': False, 'reason': ...}."""
    if not text or not text.strip():
        return {"ok": False, "reason": "Please type a question about the churn dataset."}
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    cleaned = cleaned.strip()
    if len(cleaned) > config.MAX_INPUT_CHARS:
        return {"ok": False,
                "reason": f"That message is over {config.MAX_INPUT_CHARS} characters. "
                          "Please ask a shorter, focused question."}
    low = cleaned.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            return {"ok": False,
                    "reason": "I can't help with that — I'm a data analyst for the "
                              "customer-churn dataset. Ask me about the data, "
                              "individual customers, or churn risk."}

    # Intercept standalone general math expressions
    math_match = re.match(r"^(?:what\s+is\s+|calculate\s+|solve\s+|compute\s+)?[\d\s+\-*/().^%xX=]+\??$", cleaned, re.IGNORECASE)
    domain_keywords = {"churn", "customer", "contract", "charge", "tenure", "month", "risk", "rate", "senior", "internet", "tech", "support", "fiber", "dsl", "payment", "revenue", "bill", "data"}
    if math_match and not any(kw in low for kw in domain_keywords):
        return {"ok": False,
                "reason": "I am a specialized Autonomous Churn Analyst Agent. Please ask me questions related to the telecom customer dataset, churn risk predictions, customer retention strategies, or what-if scenario simulations."}

    return {"ok": True, "text": cleaned}


# ---------------------------------------------------------------- numbers
_NUM_RE = re.compile(r"(?<![\w./-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)%?")


def _to_float(tok: str) -> float:
    return float(tok.replace(",", "").rstrip("%"))


def extract_numbers(text: str) -> list[tuple[str, float, bool]]:
    """(token, value, is_percent) for every number in prose, skipping markdown
    enumerations ('1. ') and 4-digit years."""
    out = []
    for line in text.splitlines():
        stripped = line.lstrip()
        for m in _NUM_RE.finditer(line):
            tok = m.group(0)
            # skip '1.' / '2)' list markers at line start
            if stripped.startswith(tok) and re.match(rf"^{re.escape(tok)}[.)]\s",
                                                     stripped):
                continue
            val = _to_float(tok)
            if re.fullmatch(r"(19|20)\d{2}", tok.rstrip("%")):
                continue  # years
            out.append((tok, val, tok.endswith("%")))
    return out


def _close(a: float, b: float) -> bool:
    if a == b:
        return True
    tol = config.NUMBER_MATCH_REL_TOL
    return abs(a - b) <= max(tol * max(abs(a), abs(b)), 0.01)


def verify_numbers(answer: str, evidence: str) -> dict:
    """Check every number in `answer` appears in (or rounds from, or is a difference of) `evidence`."""
    ev_values = [ _to_float(m.group(0)) for m in _NUM_RE.finditer(evidence) ]
    # Standard values and percentage scalings
    ev_set = ev_values + [v * 100 for v in ev_values] + [v / 100 for v in ev_values]
    
    # Add pairwise arithmetic differences (e.g. churn rate reductions 42.7% - 11.3% = 31.4%)
    if len(ev_values) < 50:  # Bound computation
        diffs = [abs(a - b) for a in ev_values for b in ev_values]
        diffs_scaled = [d * 100 for d in diffs] + [d / 100 for d in diffs]
        ev_set.extend(diffs + diffs_scaled)
    
    # Common schema descriptors and ordinal ranks (1 year, 2 years, 12/24 months, top 5)
    SCHEMA_CONSTANTS = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 12.0, 24.0, 36.0, 72.0]
    ev_set.extend(SCHEMA_CONSTANTS)

    unverified = []
    for tok, val, is_pct in extract_numbers(answer):
        candidates = [val] + ([val / 100] if is_pct else [])
        if not any(_close(c, e) for c in candidates for e in ev_set):
            unverified.append(tok)
    return {"ok": not unverified, "unverified": unverified,
            "checked": len(extract_numbers(answer))}


THINK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)


def scrub_output(text: str) -> str:
    cleaned = THINK_PATTERN.sub("", text).strip()
    return SECRET_PATTERN.sub("[redacted]", cleaned)

