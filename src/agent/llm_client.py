"""Provider-agnostic LLM client (Groq / OpenRouter, OpenAI-compatible).

Inference optimisations implemented here:

* **Response caching** — identical temperature-0 requests are served from an
  in-process LRU cache (repeat questions, critic re-checks, eval reruns cost
  zero tokens).
* **Retry with exponential backoff + jitter** on 429/5xx, honouring the
  ``Retry-After`` header — free tiers throttle aggressively and a naive
  retry loop burns the quota faster.
* **Model routing** — callers pass the model per call: the big planner model
  only runs for planning turns; guardrail and critic checks run on the small
  model (cheaper, faster, and it keeps the planner's rate budget free).
* **Hard token caps** per call, so a runaway generation can't eat the quota.
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from collections import OrderedDict

import requests

from .. import config


class LLMError(RuntimeError):
    pass


class LLMNotConfigured(LLMError):
    """Raised when no API key is present — the app shows a friendly banner."""


class LLMClient:
    RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 cache_size: int = config.LLM_CACHE_SIZE, max_retries: int = 5):
        self.api_key = api_key if api_key is not None else config.api_key()
        self.base_url = (base_url or config.base_url()).rstrip("/")
        self.max_retries = max_retries
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()
        self.stats = {"calls": 0, "cache_hits": 0, "retries": 0,
                      "prompt_tokens": 0, "completion_tokens": 0}

    # ------------------------------------------------------------------
    def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None,
             temperature: float = 0.0, max_tokens: int = 1024,
             force_json: bool = False) -> dict:
        """Return the assistant *message* dict ({role, content, tool_calls?})."""
        if not self.api_key:
            raise LLMNotConfigured(
                "No LLM API key configured. Copy .env.example to .env and set "
                "GROQ_API_KEY (or OPENROUTER_API_KEY).")

        payload: dict = {"model": model, "messages": messages,
                         "temperature": temperature, "max_tokens": max_tokens}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if force_json:
            payload["response_format"] = {"type": "json_object"}

        key = None
        if temperature == 0.0:
            key = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                            default=str).encode()).hexdigest()
            with self._lock:
                if key in self._cache:
                    self._cache.move_to_end(key)
                    self.stats["cache_hits"] += 1
                    return json.loads(json.dumps(self._cache[key]))

        message = self._post(payload)

        if key is not None:
            with self._lock:
                self._cache[key] = json.loads(json.dumps(message))
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
        return message

    # ------------------------------------------------------------------
    def _post(self, payload: dict) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        delay = 1.0
        last_err = "unknown error"
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
            except requests.RequestException as e:
                last_err = f"network error: {e}"
                resp = None
            if resp is not None:
                if resp.status_code == 200:
                    body = resp.json()
                    usage = body.get("usage", {})
                    self.stats["calls"] += 1
                    self.stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    self.stats["completion_tokens"] += usage.get("completion_tokens", 0)
                    return body["choices"][0]["message"]
                if resp.status_code not in self.RETRYABLE:
                    raise LLMError(f"LLM API error {resp.status_code}: {resp.text[:500]}")
                retry_after = resp.headers.get("retry-after")
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        pass
                last_err = f"HTTP {resp.status_code}"
            self.stats["retries"] += 1
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 2, 30)
        raise LLMError(f"LLM API failed after {self.max_retries} attempts ({last_err})")


class MockLLM:
    """Scripted stand-in for tests and the offline eval mode.

    ``script`` is a list of assistant message dicts; each ``chat()`` call pops
    the next one. Records every request for assertions.
    """

    def __init__(self, script: list[dict]):
        self.script = list(script)
        self.requests: list[dict] = []
        self.stats = {"calls": 0, "cache_hits": 0, "retries": 0,
                      "prompt_tokens": 0, "completion_tokens": 0}

    def chat(self, messages, model, tools=None, temperature=0.0,
             max_tokens=1024, force_json=False):
        self.requests.append({"messages": messages, "model": model,
                              "tools": tools})
        self.stats["calls"] += 1
        if not self.script:
            return {"role": "assistant",
                    "content": "Mock script exhausted — no answer available."}
        return self.script.pop(0)


def make_tool_call(name: str, arguments: dict, call_id: str = "call_1") -> dict:
    """Helper for building scripted MockLLM tool-call messages."""
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": call_id, "type": "function",
                            "function": {"name": name,
                                         "arguments": json.dumps(arguments)}}]}
