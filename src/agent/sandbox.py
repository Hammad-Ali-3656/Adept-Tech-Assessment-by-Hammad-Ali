"""Restricted code-as-tool execution.

The agent answers data questions by *running real pandas code* against the
dataframe rather than guessing. That code is LLM-generated, so it runs under
restrictions, inside our own process (per the brief — no paid sandbox):

* AST validation before execution: no imports, no dunder access, no
  ``exec``/``eval``/``open``/attribute escapes, denylisted pandas I/O.
* Empty builtins except an explicit safe allowlist.
* Namespace contains only ``df`` (a defensive copy), ``pd``, ``np``.
* Wall-clock timeout via a worker thread.
* Output size capped before it is fed back to the LLM.

This is a best-effort in-process jail against *accidental or prompted*
misuse, not a security boundary against a determined attacker — that honesty
matters and is repeated in the README.
"""
from __future__ import annotations

import ast
import contextlib
import io
import threading

import numpy as np
import pandas as pd

from .. import config

BLOCKED_NAMES = {
    "eval", "exec", "compile", "open", "input", "breakpoint", "__import__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr", "memoryview",
    "exit", "quit", "help", "dir", "super", "type", "object", "classmethod",
    "staticmethod",
}
BLOCKED_ATTRS = {
    # file / IO escapes through pandas & numpy
    "read_csv", "read_pickle", "read_json", "read_html", "read_sql", "read_excel",
    "read_parquet", "read_table", "read_clipboard", "to_csv", "to_pickle",
    "to_json", "to_sql", "to_excel", "to_parquet", "to_clipboard", "to_hdf",
    "save", "load", "fromfile", "tofile", "memmap",
    # generic escapes
    "eval", "exec", "system", "popen", "spawn", "fork", "kill",
}
SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "float": float, "int": int, "len": len,
    "list": list, "map": map, "filter": filter, "max": max, "min": min,
    "print": print, "range": range, "round": round, "set": set,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "isinstance": isinstance, "repr": repr, "divmod": divmod, "pow": pow,
    "reversed": reversed, "frozenset": frozenset, "slice": slice,
    "ValueError": ValueError, "KeyError": KeyError, "TypeError": TypeError,
    "ZeroDivisionError": ZeroDivisionError, "Exception": Exception,
}


class SandboxViolation(ValueError):
    pass


def validate(code: str) -> ast.Module:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxViolation(f"syntax error: {e}") from None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SandboxViolation("imports are not allowed — df, pd, np are preloaded")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                             ast.Global, ast.Nonlocal, ast.AsyncFor, ast.AsyncWith,
                             ast.Await)):
            raise SandboxViolation(f"{type(node).__name__} is not allowed")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise SandboxViolation(f"use of '{node.id}' is not allowed")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") or node.attr in BLOCKED_ATTRS:
                raise SandboxViolation(f"attribute '{node.attr}' is not allowed")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "__" in node.value and ("import" in node.value or "builtins" in node.value):
                raise SandboxViolation("suspicious string constant")
    return tree


def _execute(code: str, df: pd.DataFrame) -> str:
    tree = validate(code)
    # make the value of a trailing expression the result, like a notebook cell
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        tree.body[-1] = ast.Assign(
            targets=[ast.Name(id="_", ctx=ast.Store())],
            value=tree.body[-1].value)
        ast.fix_missing_locations(tree)
    ns = {"df": df.copy(), "pd": pd, "np": np,
          "__builtins__": dict(SAFE_BUILTINS)}
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exec(compile(tree, "<sandbox>", "exec"), ns)  # noqa: S102 — validated AST
    parts = []
    if stdout.getvalue().strip():
        parts.append(stdout.getvalue().strip())
    result = ns.get("result", ns.get("_"))
    if result is not None:
        if isinstance(result, pd.DataFrame):
            parts.append(result.to_string(max_rows=30, max_cols=25))
        elif isinstance(result, pd.Series):
            parts.append(result.to_string(max_rows=40))
        else:
            parts.append(repr(result))
    if not parts:
        return ("(no output — end the code with an expression, or assign to a "
                "variable named `result`, or print())")
    return "\n".join(parts)


def run(code: str, df: pd.DataFrame,
        timeout: float = config.SANDBOX_TIMEOUT_SECONDS) -> dict:
    """Execute and return {'ok': bool, 'output' | 'error': str}."""
    # A daemon thread (not ThreadPoolExecutor) so a runaway execution can
    # never keep the process alive — it dies with the interpreter.
    box: dict = {}

    def _worker():
        try:
            box["out"] = _execute(code, df)
        except BaseException as e:  # noqa: BLE001 — marshalled to caller
            box["exc"] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return {"ok": False,
                "error": f"execution exceeded {timeout}s — simplify the query"}
    if "exc" in box:
        e = box["exc"]
        if isinstance(e, SandboxViolation):
            return {"ok": False, "error": f"blocked by sandbox: {e}"}
        # pandas errors etc. go back to the LLM to self-correct
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    out = box.get("out", "")
    if len(out) > config.TOOL_OUTPUT_CHAR_LIMIT:
        out = (out[:config.TOOL_OUTPUT_CHAR_LIMIT]
               + f"\n…[truncated at {config.TOOL_OUTPUT_CHAR_LIMIT} chars — "
                 "aggregate more before returning]")
    return {"ok": True, "output": out}
