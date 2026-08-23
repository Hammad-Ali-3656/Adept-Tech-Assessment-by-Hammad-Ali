"""Tool layer: everything the agent can actually *do*.

Each tool returns a JSON-serialisable dict. Whatever a tool returns is the
only ground truth the agent may quote numbers from — the verifier
(guardrails + critic) enforces that.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .. import config
from ..data_prep import ALL_FEATURES, ID_COL, NUMERIC_FEATURES, TARGET
from . import sandbox


class ToolBelt:
    """Binds the tools to a dataframe + model and records every invocation."""

    def __init__(self, df: pd.DataFrame, model):
        self.df = df
        self.model = model
        # sandbox/chart view of the data includes precomputed model scores so
        # "revenue for high-risk customers"-style questions are one query away
        self.df_risk = df.assign(model_risk=np.round(model.score_frame(df), 4))
        self.charts: list = []          # plotly figures produced this episode
        self.trace: list[dict] = []     # [{tool, arguments, result}]

    # ================= tool implementations =================
    def run_python(self, code: str) -> dict:
        res = sandbox.run(code, self.df_risk)
        return res

    def predict_churn(self, customer_id: str) -> dict:
        return self.model.predict_churn_risk(customer_id, self.df)

    def what_if(self, customer_id: str, overrides: dict) -> dict:
        return self.model.what_if(customer_id, overrides, self.df)

    def predict_hypothetical(self, features: dict) -> dict:
        return self.model.predict_hypothetical(features)

    def segment_risk(self, group_by: list[str] | str | None = None,
                     filter_query: str | None = None) -> dict:
        """Aggregate *model* churn risk (and actual churn rate) by segment."""
        df = self.df_risk
        if filter_query:
            try:
                df = df.query(filter_query)
            except Exception as e:
                return {"ok": False, "error": f"bad filter_query: {e}"}
        if df.empty:
            return {"ok": False, "error": "filter matched 0 customers"}
        scores = self.model.score_frame(df)
        work = df.assign(_risk=scores, _churned=(df[TARGET] == "Yes"))
        if group_by:
            group_by = [group_by] if isinstance(group_by, str) else list(group_by)
            bad = [c for c in group_by if c not in df.columns]
            if bad:
                return {"ok": False, "error": f"unknown column(s): {bad}"}
            agg = (work.groupby(group_by, observed=True)
                       .agg(customers=("_risk", "size"),
                            avg_model_risk=("_risk", "mean"),
                            actual_churn_rate=("_churned", "mean"))
                       .round(4).reset_index())
            return {"ok": True, "group_by": group_by,
                    "filter_query": filter_query,
                    "segments": agg.to_dict(orient="records")}
        return {"ok": True, "filter_query": filter_query,
                "customers": int(len(work)),
                "avg_model_risk": round(float(work["_risk"].mean()), 4),
                "actual_churn_rate": round(float(work["_churned"].mean()), 4)}

    def data_summary(self, aspect: str = "schema", column: str | None = None) -> dict:
        df = self.df
        if aspect == "schema":
            return {"ok": True, "rows": int(len(df)),
                    "columns": {c: str(df[c].dtype) for c in df.columns},
                    "id_column": ID_COL, "target": TARGET,
                    "model_features": ALL_FEATURES,
                    "churn_rate": round(float((df[TARGET] == "Yes").mean()), 4)}
        if aspect == "describe":
            num = df.select_dtypes(include=np.number).describe().round(3)
            return {"ok": True, "numeric_describe": json.loads(num.to_json())}
        if aspect == "value_counts":
            if not column or column not in df.columns:
                return {"ok": False, "error": f"pass a valid column; got {column!r}"}
            vc = df[column].value_counts(dropna=False)
            return {"ok": True, "column": column,
                    "value_counts": {str(k): int(v) for k, v in vc.items()}}
        if aspect == "churn_rate_by":
            if not column or column not in df.columns:
                return {"ok": False, "error": f"pass a valid column; got {column!r}"}
            col = df[column]
            if column in NUMERIC_FEATURES:
                col = pd.qcut(col, 4, duplicates="drop").astype(str)
            g = (df.assign(_churned=(df[TARGET] == "Yes"), _b=col)
                   .groupby("_b", observed=True)["_churned"]
                   .agg(customers="size", churn_rate="mean").round(4))
            return {"ok": True, "column": column,
                    "churn_rate_by": json.loads(g.reset_index()
                                                 .rename(columns={"_b": column})
                                                 .to_json(orient="records"))}
        if aspect == "missing":
            return {"ok": True,
                    "missing_per_column": {c: int(df[c].isna().sum())
                                           for c in df.columns},
                    "note": "cleaning already ran: TotalCharges blanks were "
                            "imputed to 0 for tenure-0 customers (NewCustomer='Yes')"}
        return {"ok": False,
                "error": "aspect must be one of: schema, describe, value_counts, "
                         "churn_rate_by, missing"}

    def make_chart(self, kind: str, x: str, y: str | None = None,
                   agg: str = "mean", color: str | None = None,
                   filter_query: str | None = None, title: str | None = None,
                   bins: int = 30) -> dict:
        """Deterministic chart builder (no LLM-generated plotting code)."""
        import plotly.express as px

        df = self.df_risk
        if filter_query:
            try:
                df = df.query(filter_query)
            except Exception as e:
                return {"ok": False, "error": f"bad filter_query: {e}"}
        if df.empty:
            return {"ok": False, "error": "filter matched 0 customers"}
        special = {"churn_rate"}
        for c in [x, y, color]:
            if c and c not in set(df.columns) | special:
                return {"ok": False, "error": f"unknown column {c!r}"}

        try:
            if kind == "hist":
                fig = px.histogram(df, x=x, color=color, nbins=bins, title=title)
                data_note = {"count": int(len(df))}
            elif kind == "box":
                fig = px.box(df, x=x, y=y, color=color, title=title)
                data_note = {"count": int(len(df))}
            elif kind == "scatter":
                sample = df.sample(min(len(df), 2000), random_state=0)
                fig = px.scatter(sample, x=x, y=y, color=color, title=title,
                                 opacity=0.5)
                data_note = {"points_plotted": int(len(sample))}
            elif kind in {"bar", "line"}:
                if y is None:
                    return {"ok": False, "error": f"{kind} needs both x and y"}
                if agg not in {"mean", "sum", "count", "median"}:
                    return {"ok": False, "error": "agg must be mean/sum/count/median"}
                ycol = y
                work = df
                if y == "churn_rate":
                    work = df.assign(churn_rate=(df[TARGET] == "Yes").astype(float))
                    agg, ycol = "mean", "churn_rate"
                keys = [x] + ([color] if color else [])
                g = (work.groupby(keys, observed=True)[ycol]
                         .agg(agg).round(4).reset_index())
                fn = px.bar if kind == "bar" else px.line
                fig = fn(g, x=x, y=ycol, color=color, title=title)
                data_note = {"aggregated_data": g.to_dict(orient="records")}
            else:
                return {"ok": False,
                        "error": "kind must be one of: hist, box, scatter, bar, line"}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

        fig.update_layout(template="plotly_white", height=420)
        self.charts.append(fig)
        return {"ok": True, "chart_index": len(self.charts) - 1,
                "note": "chart rendered to the user", **data_note}

    # ================= dispatch =================
    def dispatch(self, name: str, arguments: dict) -> dict:
        fn = {
            "run_python": self.run_python,
            "predict_churn": self.predict_churn,
            "what_if": self.what_if,
            "predict_hypothetical": self.predict_hypothetical,
            "segment_risk": self.segment_risk,
            "data_summary": self.data_summary,
            "make_chart": self.make_chart,
        }.get(name)
        if fn is None:
            result = {"ok": False, "error": f"unknown tool {name!r}"}
        else:
            try:
                result = fn(**arguments)
                if isinstance(result, dict) and "ok" not in result:
                    result = {"ok": True, **result}
            except TypeError as e:
                result = {"ok": False, "error": f"bad arguments: {e}"}
            except (KeyError, ValueError) as e:
                result = {"ok": False, "error": str(e)}
            except Exception as e:
                result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        self.trace.append({"tool": name, "arguments": arguments, "result": result})
        return result

    def evidence_text(self) -> str:
        """Everything computed this episode — the critic checks answers against this."""
        return "\n".join(json.dumps({"tool": t["tool"], "arguments": t["arguments"],
                                     "result": t["result"]}, default=str)
                         for t in self.trace)


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "run_python",
        "description": ("Run restricted pandas code against the cleaned churn "
                        "dataframe `df` (pd and np preloaded; no imports/files). "
                        "`df` includes a precomputed `model_risk` column (model "
                        "churn probability per customer). End with an expression "
                        "or assign to `result`. Use for aggregations, filters, "
                        "correlations, trends, EDA."),
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "Python/pandas code"}},
            "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "predict_churn",
        "description": ("Model churn risk for ONE existing customer: risk_score, "
                        "risk_band, top_factors."),
        "parameters": {"type": "object", "properties": {
            "customer_id": {"type": "string"}}, "required": ["customer_id"]}}},
    {"type": "function", "function": {
        "name": "what_if",
        "description": ("Projected churn risk for an existing customer if some "
                        "features changed (e.g. Contract -> 'Two year'). Returns "
                        "current vs projected risk."),
        "parameters": {"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "overrides": {"type": "object",
                          "description": "feature -> new value"}},
            "required": ["customer_id", "overrides"]}}},
    {"type": "function", "function": {
        "name": "predict_hypothetical",
        "description": ("Churn risk for a NEW hypothetical customer described by "
                        "feature values; unspecified features default to dataset "
                        "baseline (mode/median)."),
        "parameters": {"type": "object", "properties": {
            "features": {"type": "object",
                         "description": "feature -> value, e.g. {\"tenure\": 2, "
                                        "\"Contract\": \"Month-to-month\"}"}},
            "required": ["features"]}}},
    {"type": "function", "function": {
        "name": "segment_risk",
        "description": ("Average MODEL churn risk + actual churn rate, overall or "
                        "grouped by column(s), optionally filtered with a pandas "
                        "query string."),
        "parameters": {"type": "object", "properties": {
            "group_by": {"type": "array", "items": {"type": "string"}},
            "filter_query": {"type": "string",
                             "description": "pandas df.query filter, e.g. "
                                            "\"Contract == 'Month-to-month'\""}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "data_summary",
        "description": ("Quick EDA summaries: aspect='schema' | 'describe' | "
                        "'value_counts' | 'churn_rate_by' | 'missing' "
                        "(value_counts / churn_rate_by need `column`)."),
        "parameters": {"type": "object", "properties": {
            "aspect": {"type": "string"},
            "column": {"type": "string"}}, "required": ["aspect"]}}},
    {"type": "function", "function": {
        "name": "make_chart",
        "description": ("Render a chart for the user. kind: hist|box|scatter|bar|"
                        "line. Special y value 'churn_rate' plots actual churn "
                        "rate; special column 'model_risk' uses model scores. "
                        "Returns the aggregated numbers used."),
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string"}, "x": {"type": "string"},
            "y": {"type": "string"}, "agg": {"type": "string"},
            "color": {"type": "string"}, "filter_query": {"type": "string"},
            "title": {"type": "string"}, "bins": {"type": "integer"}},
            "required": ["kind", "x"]}}},
]
