"""Critic agent — second pair of eyes before an answer reaches the user.

Two layers, cheapest first:
1. Deterministic number verification (guardrails.verify_numbers) — no
   tokens spent, catches invented figures outright.
2. LLM critic on the SMALL model — semantic check: does the draft answer
   the question, do comparisons match the evidence direction, is anything
   claimed that was never computed.

Returns a verdict the loop uses to retry (with the critic's reason fed
back to the planner) or to deliver with an explicit caution flag.
"""
from __future__ import annotations

import json
import re

from .. import config
from . import guardrails
from .prompts import CRITIC_SYSTEM


def review(question: str, draft: str, evidence: str, llm, small_model: str | None = None) -> dict:
    """-> {'verdict': 'pass'|'fail', 'reason': str, 'unverified_numbers': [...]}"""
    nums = guardrails.verify_numbers(draft, evidence)
    if not nums["ok"]:
        return {"verdict": "fail",
                "reason": ("these figures do not trace to any tool result: "
                           + ", ".join(nums["unverified"])
                           + ". Recompute them or remove them."),
                "unverified_numbers": nums["unverified"]}

    if llm is None:  # deterministic-only mode (no key / tests)
        return {"verdict": "pass", "reason": "deterministic checks passed "
                                             "(LLM critic skipped)",
                "unverified_numbers": []}

    try:
        msg = llm.chat(
            messages=[{"role": "system", "content": CRITIC_SYSTEM},
                      {"role": "user", "content":
                       f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence[:6000]}"
                       f"\n\nDRAFT ANSWER:\n{draft}"}],
            model=small_model or config.SMALL_MODEL,
            temperature=0.0, max_tokens=200, force_json=True)
        raw = (msg.get("content") or "").strip()
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {}
        verdict = data.get("verdict", "pass")
        return {"verdict": "fail" if verdict == "fail" else "pass",
                "reason": data.get("reason", ""), "unverified_numbers": []}
    except Exception as e:
        # A broken critic must not block a numerically-verified answer.
        return {"verdict": "pass",
                "reason": f"LLM critic unavailable ({type(e).__name__}); "
                          "deterministic checks passed",
                "unverified_numbers": []}
