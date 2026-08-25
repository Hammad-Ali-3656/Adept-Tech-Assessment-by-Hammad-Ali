"""The agent loop: plan → act (tools) → observe → self-check → answer.

Flow for one question:

1. Input guardrail (deterministic) — refuse injections / oversize input.
2. Planner LLM (big model) with native tool-calling; a JSON-in-content
   fallback keeps things working on models without tool support.
3. Tools execute; results (truncated to a char budget) go back into the
   conversation. Errors go back too — the planner is expected to correct
   itself (rule 3 of its prompt), and empty/failed results never
   silently disappear.
4. When the planner produces a final text answer, the CRITIC reviews it
   (deterministic number-tracing first, then a small-model semantic
   check). On failure the reason is appended to the conversation and the
   planner gets another attempt (up to 2 critic retries).
5. If it still fails, the answer ships with an explicit caution flag —
   honest degradation instead of confident garbage.
6. Output scrubbed for secrets; the exchange is stored in Memory with a
   compact fact line so follow-up questions can build on it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .. import config
from . import guardrails
from .critic import review
from .llm_client import LLMClient, LLMNotConfigured
from .memory import Memory
from .prompts import JSON_FALLBACK_INSTRUCTIONS, PLANNER_SYSTEM
from .tools import TOOL_SCHEMAS, ToolBelt

MAX_CRITIC_RETRIES = 1


@dataclass
class AgentResponse:
    answer: str
    charts: list = field(default_factory=list)
    steps: list = field(default_factory=list)       # human-readable trace
    verification: dict = field(default_factory=dict)
    ok: bool = True


class AnalystAgent:
    def __init__(self, df, model, llm=None, planner_model: str | None = None,
                 small_model: str | None = None, use_llm_critic: bool = True,
                 max_steps: int = config.MAX_AGENT_STEPS):
        self.df = df
        self.model = model
        self.llm = llm if llm is not None else LLMClient()
        self.planner_model = planner_model or config.PLANNER_MODEL
        self.small_model = small_model or config.SMALL_MODEL
        self.use_llm_critic = use_llm_critic
        self.max_steps = max_steps
        self.memory = Memory()

    # ------------------------------------------------------------------
    def ask(self, question: str) -> AgentResponse:
        guard = guardrails.check_input(question)
        if not guard["ok"]:
            return AgentResponse(answer=guard["reason"], ok=False,
                                 verification={"input_guard": "refused"})
        question = guard["text"]

        belt = ToolBelt(self.df, self.model)
        steps: list[str] = []
        messages = ([{"role": "system", "content": PLANNER_SYSTEM}]
                    + self.memory.context_messages()
                    + [{"role": "user", "content": question}])

        try:
            draft = self._run_tool_loop(messages, belt, steps)
            draft, verification = self._checked_answer(question, draft,
                                                       messages, belt, steps)
        except LLMNotConfigured as e:
            return AgentResponse(answer=str(e), ok=False,
                                 verification={"error": "llm_not_configured"})
        except Exception as e:
            return AgentResponse(
                answer=f"⚠️ {type(e).__name__}: {e}",
                steps=steps, ok=False,
                verification={"error": f"{type(e).__name__}: {e}"})

        answer = guardrails.scrub_output(draft)
        facts = self._fact_line(belt)
        self.memory.add_exchange(question, answer, facts)
        return AgentResponse(answer=answer, charts=belt.charts, steps=steps,
                             verification=verification)

    # ------------------------------------------------------------------
    def _run_tool_loop(self, messages: list[dict], belt: ToolBelt,
                       steps: list[str]) -> str:
        json_fallback = False
        for _ in range(self.max_steps):
            msg = self.llm.chat(messages=self._budgeted(messages),
                                model=self.planner_model,
                                tools=None if json_fallback else TOOL_SCHEMAS,
                                temperature=0.0, max_tokens=2048)
            tool_calls = msg.get("tool_calls") or []
            content = (msg.get("content") or "").strip()

            if not tool_calls and not json_fallback:
                # Check for Qwen / Hermes XML tool call format
                xml_calls = self._parse_xml_tool_calls(content)
                if xml_calls:
                    tool_calls = xml_calls
                else:
                    # model may have emitted a JSON tool call as plain text
                    parsed = self._parse_json_tool_call(content)
                    if parsed and "tool" in parsed:
                        tool_calls = [{"id": "fb_1", "type": "function",
                                       "function": {"name": parsed["tool"],
                                                    "arguments": json.dumps(
                                                        parsed.get("arguments", {}))}}]
                    elif parsed and "final_answer" in parsed:
                        return str(parsed["final_answer"])

            if tool_calls:
                messages.append({"role": "assistant", "content": msg.get("content"),
                                 "tool_calls": tool_calls})
                for tc in tool_calls[:4]:  # cap parallel calls per turn
                    name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"] or "{}")
                        if not isinstance(args, dict):
                            raise ValueError("arguments must be an object")
                    except (json.JSONDecodeError, ValueError) as e:
                        result = {"ok": False,
                                  "error": f"malformed tool arguments: {e}"}
                        belt.trace.append({"tool": name, "arguments": {},
                                           "result": result})
                    else:
                        result = belt.dispatch(name, args)
                    steps.append(self._describe_step(name, result, belt))
                    messages.append({
                        "role": "tool", "tool_call_id": tc["id"],
                        "content": json.dumps(result, default=str)
                        [:config.TOOL_OUTPUT_CHAR_LIMIT]})
                continue

            if content:
                cleaned_content = self._clean_llm_output(content)
                if cleaned_content:
                    return cleaned_content

            # Empty response with no tool call: switch to the JSON fallback
            # protocol once (handles models without native tool support).
            if not json_fallback:
                json_fallback = True
                messages.append({"role": "system",
                                 "content": JSON_FALLBACK_INSTRUCTIONS})
                continue
            break

        # Step budget reached or tools executed — synthesize final answer in markdown
        messages.append({"role": "system",
                         "content": "Synthesize your final executive answer NOW using the tool results above. "
                                    "Format with clear markdown headings, bullet points, and key findings. "
                                    "DO NOT output <think> blocks, code, or XML tags."})
        msg = self.llm.chat(messages=self._budgeted(messages),
                            model=self.planner_model, tools=None, temperature=0.0,
                            max_tokens=2048)
        raw_out = msg.get("content") or ""
        cleaned_out = self._clean_llm_output(raw_out)
        if not cleaned_out:
            cleaned_out = self._synthesize_evidence_fallback(belt)
        return cleaned_out

    # ------------------------------------------------------------------
    def _checked_answer(self, question: str, draft: str, messages: list[dict],
                        belt: ToolBelt, steps: list[str]) -> tuple[str, dict]:
        if not draft or not draft.strip():
            draft = self._synthesize_evidence_fallback(belt)
        evidence = belt.evidence_text()
        verification: dict = {"tool_calls": len(belt.trace)}
        if not belt.trace and guardrails.extract_numbers(draft):
            # numbers with zero computation → force one retry through critic path
            steps.append("self-check: answer contains figures but no tool was "
                         "called — sending back to the planner")
        critic_llm = self.llm if self.use_llm_critic else None
        for attempt in range(MAX_CRITIC_RETRIES + 1):
            result = review(question, draft, evidence, critic_llm,
                            self.small_model)
            verification["critic"] = result
            if result["verdict"] == "pass":
                steps.append(f"critic: pass ({result['reason'] or 'supported by evidence'})")
                return draft, verification
            steps.append(f"critic: FAIL — {result['reason']}")
            if attempt == MAX_CRITIC_RETRIES:
                break
            messages.append({"role": "assistant", "content": draft})
            messages.append({"role": "system",
                             "content": ("Your draft answer was rejected by a "
                                         f"fact-checker: {result['reason']} "
                                         "Fix it — recompute with tools if "
                                         "needed, then answer again.")})
            draft = self._run_tool_loop(messages, belt, steps)
            if not draft or not draft.strip():
                draft = self._synthesize_evidence_fallback(belt)
            evidence = belt.evidence_text()
        verification["flagged"] = True
        return (draft + "\n\n⚠️ *Caution: I could not fully verify parts of this "
                        "answer against computed results — treat the flagged "
                        "figures as unconfirmed.*"), verification

    # ------------------------------------------------------------------
    def _budgeted(self, messages: list[dict]) -> list[dict]:
        """Token-budget compaction: keep system + recent turns; squash old
        tool payloads (inference optimisation for long episodes)."""
        if len(messages) <= 24:
            return messages
        head = [m for m in messages[:2]]
        tail = messages[-20:]
        squashed = [{"role": "system",
                     "content": f"[{len(messages) - len(head) - len(tail)} earlier "
                                "steps compacted]"}]
        return head + squashed + tail

    @classmethod
    def _clean_llm_output(cls, text: str) -> str:
        """Strip CoT think blocks (including unclosed blocks), XML tool call markup, and rogue tags from final answers."""
        if not text:
            return ""
        cleaned = re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL)
        cleaned = re.sub(r"<tool_call>.*?(?:</tool_call>|$)", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<function[=\s][^>]*>.*?(?:</function>|$)", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"</?(?:tool_call|function|parameter)[^>]*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"```json\s*\{\s*\"tool\":.*?\}\s*```", "", cleaned, flags=re.DOTALL)
        return cleaned.strip()


    @classmethod
    def _synthesize_evidence_fallback(cls, belt: ToolBelt) -> str:
        """Generate structured executive summary from tool trace if model outputs only raw XML."""
        if not belt.trace:
            return "No specific customer or churn data was found for this query."
        lines = ["### Churn Analysis Summary\n"]
        for item in belt.trace:
            tool = item.get("tool")
            res = item.get("result")
            if tool == "segment_risk" and isinstance(res, list):
                grp = ", ".join(item.get("arguments", {}).get("group_by", [])) or "Segment"
                lines.append(f"**Breakdown by {grp}:**")
                for r in res:
                    label = next((str(v) for k, v in r.items() if k not in ["count", "actual_churn_rate", "avg_model_risk", "high_risk_count"]), "Category")
                    lines.append(f"- **{label}**: Churn Rate {r.get('actual_churn_rate', 0):.1%}, Avg Risk {r.get('avg_model_risk', 0):.1%}, Customers {r.get('count', 0):,}")
            elif tool == "predict_churn" and isinstance(res, dict):
                lines.append(f"- **Customer {res.get('customer_id', '')}**: Risk Score {res.get('risk_score', 0):.1%} ({res.get('risk_category', '')} risk).")
            elif tool == "what_if" and isinstance(res, dict):
                lines.append(f"- **What-If Simulation**: Current Risk {res.get('current_risk', 0):.1%} -> Projected Risk {res.get('projected_risk', 0):.1%} (Delta: {res.get('delta', 0):+.1%}).")
        return "\n".join(lines)

    @classmethod
    def _parse_xml_tool_calls(cls, content: str) -> list[dict]:
        """Parse Qwen / Hermes XML tool calls: <tool_call><function=name><parameter=k>v</parameter></function></tool_call>"""
        if not content:
            return []
        
        tool_calls = []
        blocks = re.findall(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
        if not blocks and ("<function=" in content or "<function " in content):
            blocks = [content]

        for i, block in enumerate(blocks):
            fn_matches = re.finditer(r"<function[=\s](?:name=)?[\"']?([a-zA-Z0-9_]+)[\"']?>(.*?)(?:</function>|$)", block, re.DOTALL)
            for j, fn_match in enumerate(fn_matches):
                fn_name = fn_match.group(1).strip()
                fn_body = fn_match.group(2)
                param_matches = re.findall(r"<parameter[=\s](?:name=)?[\"']?([a-zA-Z0-9_]+)[\"']?>(.*?)(?:</parameter>|$)", fn_body, re.DOTALL)
                args = {}
                for k, v in param_matches:
                    v = v.strip()
                    try:
                        args[k] = json.loads(v)
                    except Exception:
                        args[k] = v
                
                tool_calls.append({
                    "id": f"qwen_tc_{i}_{j}",
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": json.dumps(args)
                    }
                })
        return tool_calls

    @staticmethod
    def _parse_json_tool_call(content: str):
        if not content:
            return None
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _describe_step(name: str, result: dict, belt: ToolBelt) -> str:
        args = belt.trace[-1]["arguments"] if belt.trace else {}
        ok = result.get("ok", True)
        brief = {k: v for k, v in list(args.items())[:2]}
        return (f"tool {name}({json.dumps(brief, default=str)[1:-1][:120]}) → "
                + ("ok" if ok else f"ERROR: {result.get('error', '?')[:120]}"))

    @staticmethod
    def _fact_line(belt: ToolBelt) -> str:
        """One compact line of computed facts for the memory summary."""
        bits = []
        for t in belt.trace[-4:]:
            r = t["result"]
            if not r.get("ok", True):
                continue
            if t["tool"] == "predict_churn":
                bits.append(f"{r.get('customer_id')}: risk {r.get('risk_score')}")
            elif t["tool"] == "what_if":
                bits.append(f"{r.get('customer_id')}: {r.get('current_risk')}"
                            f"->{r.get('projected_risk')} with {t['arguments'].get('overrides')}")
            elif t["tool"] == "segment_risk" and "segments" in r:
                bits.append(f"segment risk by {r.get('group_by')}")
            elif t["tool"] == "run_python":
                out = str(r.get("output", ""))[:80].replace("\n", " ")
                bits.append(f"computed: {out}")
        return "; ".join(bits)[:400]
