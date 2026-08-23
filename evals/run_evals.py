"""Eval harness: accuracy + hallucination rate over a fixed question set.

Ground truth in eval_set.json was computed directly from the cleaned
dataset and the saved model artifact (deterministic — model training is
seeded), so a correct agent answer must reproduce those figures.

Two modes:
* --live  : the real planner LLM answers every question (needs an API key).
* --mock  : the planner is replaced by the scripted plan in eval_set.json;
            the plans call the REAL tools against the REAL data, and the
            whole verification stack (sandbox, guardrails, critic number
            tracing) runs unchanged. This validates everything except the
            LLM's own planning, and is what CI / keyless environments run.

Scoring per question:
* correct        — every expected value appears in the answer (percent/
                   fraction equivalence, 2% relative tolerance)
* hallucination  — the pipeline shipped the answer with a verification
                   flag, or an expected refusal/graceful-failure leaked
                   fabricated numbers

Usage:
    python -m evals.run_evals --mock
    python -m evals.run_evals --live
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.agent import AnalystAgent
from src.agent.guardrails import extract_numbers
from src.agent.llm_client import MockLLM, make_tool_call
from src.data_prep import load_clean
from src.model import ChurnModel

HERE = Path(__file__).parent
REL_TOL = 0.02


def value_in_answer(answer: str, expected: float) -> bool:
    for _tok, val, is_pct in extract_numbers(answer):
        cands = {val, val / 100} if is_pct else {val, val / 100, val * 100}
        for c in cands:
            if expected == 0:
                if abs(c) < 1e-9:
                    return True
            elif abs(c - expected) <= max(REL_TOL * abs(expected), 0.005):
                return True
    return False


def build_mock(script_spec: list[dict]) -> MockLLM:
    script = []
    for i, step in enumerate(script_spec):
        if "tool" in step:
            script.append(make_tool_call(step["tool"], step["arguments"],
                                         f"call_{i}"))
        else:
            script.append({"role": "assistant", "content": step["final"]})
    return MockLLM(script)


def run(mode: str) -> dict:
    spec = json.loads((HERE / "eval_set.json").read_text())
    df = load_clean()
    model = ChurnModel.load()

    rows = []
    for item in spec["items"]:
        if mode == "mock":
            agent = AnalystAgent(df, model, llm=build_mock(item["mock_script"]),
                                 use_llm_critic=False)
        else:
            agent = AnalystAgent(df, model)  # fresh agent -> no memory bleed
        resp = agent.ask(item["question"])

        expected = item.get("expect_values", [])
        missing = [v for v in expected if not value_in_answer(resp.answer, v)]
        correct = not missing
        if item.get("expect_refusal"):
            correct = (not resp.ok) or any(
                p in resp.answer.lower() for p in ["can't", "cannot", "won't"])
        if item.get("expect_contains_any"):
            correct = correct and any(s.lower() in resp.answer.lower()
                                      for s in item["expect_contains_any"])

        flagged = bool(resp.verification.get("flagged"))
        hallucinated = flagged or (item.get("expect_no_hallucination", False)
                                   and flagged)
        rows.append({
            "id": item["id"], "question": item["question"],
            "correct": bool(correct), "hallucination_flag": hallucinated,
            "missing_values": missing,
            "tool_calls": resp.verification.get("tool_calls", 0),
            "answer": resp.answer,
        })
        print(f"[{'PASS' if correct else 'FAIL'}] {item['id']}"
              + (" ⚠️hallucination-flag" if hallucinated else ""))

    n = len(rows)
    summary = {
        "mode": mode,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "questions": n,
        "accuracy": round(sum(r["correct"] for r in rows) / n, 4),
        "hallucination_rate": round(
            sum(r["hallucination_flag"] for r in rows) / n, 4),
        "results": rows,
    }
    (HERE / f"eval_results_{mode}.json").write_text(
        json.dumps(summary, indent=2))
    write_report(summary)
    return summary


def write_report(s: dict) -> None:
    lines = [
        "# Eval report — churn analyst agent",
        "",
        f"- **Mode:** `{s['mode']}`"
        + (" (scripted planner over real tools + real verification stack; "
           "rerun with `--live` once an API key is set)" if s["mode"] == "mock"
           else " (real LLM planning end-to-end)"),
        f"- **Run at:** {s['run_at']}",
        f"- **Questions:** {s['questions']}",
        f"- **Accuracy:** {s['accuracy']:.0%}",
        f"- **Hallucination rate** (answers shipped with an unverified-figure "
        f"flag): {s['hallucination_rate']:.0%}",
        "",
        "| # | Question | Correct | Halluc. flag | Tool calls |",
        "|---|----------|---------|--------------|-----------|",
    ]
    for r in s["results"]:
        lines.append(f"| {r['id']} | {r['question'][:60]} | "
                     f"{'✅' if r['correct'] else '❌'} | "
                     f"{'⚠️' if r['hallucination_flag'] else '—'} | "
                     f"{r['tool_calls']} |")
    lines += [
        "",
        "## What this measures",
        "",
        "*Accuracy*: every ground-truth figure (precomputed from the data/"
        "model) must appear in the agent's answer, accepting rounding and "
        "percent-vs-fraction forms. *Hallucination rate*: how often the "
        "pipeline had to ship an answer whose figures could not be traced "
        "to computed tool results (the deterministic verifier + critic "
        "flag these explicitly rather than hiding them).",
        "",
        "Two adversarial items are included: a question about a column that "
        "doesn't exist (q13 — must fail gracefully, no invented numbers) and "
        "a prompt-injection attempt (q14 — must be refused by the input "
        "guardrail before any LLM call).",
    ]
    (HERE / "eval_report.md").write_text("\n".join(lines))
    print(f"\naccuracy={s['accuracy']:.0%}  "
          f"hallucination_rate={s['hallucination_rate']:.0%}  "
          f"-> evals/eval_report.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()
    mode = "live" if args.live else "mock"
    if mode == "live" and not config.api_key():
        raise SystemExit("No API key configured — set one in .env or run --mock")
    run(mode)
