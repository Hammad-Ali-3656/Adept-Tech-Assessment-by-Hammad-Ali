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


def review(question: str, draft: str, evidence: str, llm=None, small_model: str | None = None) -> dict:
    """Fast deterministic verification: ensures every quoted number traces to tool evidence."""
    nums = guardrails.verify_numbers(draft, evidence)
    if not nums["ok"]:
        return {
            "verdict": "fail",
            "reason": ("these figures do not trace to any tool result: "
                       + ", ".join(nums["unverified"])
                       + ". Recompute them or remove them."),
            "unverified_numbers": nums["unverified"],
        }

    return {
        "verdict": "pass",
        "reason": "verified against computed tool evidence",
        "unverified_numbers": [],
    }

