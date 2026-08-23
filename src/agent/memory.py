"""Multi-turn conversation memory with token-budget compaction.

Keeps the planner context small (inference optimisation) while making
follow-ups like "now break that down by contract type" work:

* full user/assistant turn history is kept,
* but only the last ``keep_recent`` turns go to the planner verbatim,
* older turns are compacted into a rolling plain-text summary of facts and
  definitions established earlier (e.g. which customers were called
  high-risk, what threshold was used).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Memory:
    keep_recent: int = 6            # messages (3 exchanges) passed verbatim
    turns: list[dict] = field(default_factory=list)
    summary_lines: list[dict] = field(default_factory=list)

    def add_exchange(self, user: str, assistant: str, facts: str = "") -> None:
        self.turns.append({"role": "user", "content": user})
        self.turns.append({"role": "assistant", "content": assistant})
        if facts:
            self.summary_lines.append({"q": user[:120], "facts": facts[:400]})
        # compact: drop verbatim turns beyond budget (facts survive in summary)
        while len(self.turns) > self.keep_recent:
            self.turns.pop(0)
        while len(self.summary_lines) > 10:
            self.summary_lines.pop(0)

    def context_messages(self) -> list[dict]:
        msgs: list[dict] = []
        if self.summary_lines:
            summary = "\n".join(f"- Q: {s['q']} -> {s['facts']}"
                                for s in self.summary_lines)
            msgs.append({"role": "system",
                         "content": "Facts established earlier in this "
                                    f"conversation (reuse, don't recompute "
                                    f"unless asked):\n{summary}"})
        msgs.extend(self.turns)
        return msgs

    def clear(self) -> None:
        self.turns.clear()
        self.summary_lines.clear()
