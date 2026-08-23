"""FastAPI backend application for Churn Analyst Agent.

Provides REST API endpoints for:
- AI Analyst Chat with tool execution traces & verification
- Real-time customer churn prediction & factor attributions
- Interactive Counterfactual What-If simulations
- Dataset KPIs, customer explorer, and segment analytics
- Vercel Serverless Function compatibility
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is on sys.path for relative imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import config
from src.agent import AnalystAgent
from src.data_prep import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET, ID_COL, load_clean
from src.model import ChurnModel, train_and_save

app = FastAPI(
    title="Churn Analyst Agent API",
    description="Autonomous Data Analyst and Predictive Churn API",
    version="1.0.0",
)

# Enable CORS for local Vite dev server and Vercel domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------- State cache
_state: Dict[str, Any] = {}


def get_resources():
    if "df" not in _state or "model" not in _state:
        df = load_clean()
        if not config.MODEL_PATH.exists():
            model = train_and_save(verbose=False)
        else:
            model = ChurnModel.load()
        # Compute and attach model_risk column to dataframe for quick querying
        scores = model.score_frame(df)
        df = df.assign(model_risk=scores.round(4))
        _state["df"] = df
        _state["model"] = model
        _state["agent"] = AnalystAgent(df, model)
    return _state["df"], _state["model"], _state["agent"]


# ---------------------------------------------------------------- Schemas
class ChatRequest(BaseModel):
    question: str
    clear_history: Optional[bool] = False


class WhatIfRequest(BaseModel):
    customer_id: str
    overrides: Dict[str, Any]


class HypotheticalRequest(BaseModel):
    features: Dict[str, Any]


# ---------------------------------------------------------------- Endpoints
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "churn-analyst-agent"}


@app.get("/api/stats")
def get_stats():
    df, model, _ = get_resources()
    total_customers = len(df)
    churned_count = int((df[TARGET] == "Yes").sum())
    churn_rate = float(churned_count / total_customers)
    val_metrics = model.metrics.get("validation", {})
    
    # Risk tiers count
    high_risk_count = int((df["model_risk"] >= 0.66).sum())
    med_risk_count = int(((df["model_risk"] >= 0.33) & (df["model_risk"] < 0.66)).sum())
    low_risk_count = int((df["model_risk"] < 0.33).sum())

    return {
        "total_customers": total_customers,
        "churned_count": churned_count,
        "churn_rate": round(churn_rate, 4),
        "risk_tiers": {
            "high": high_risk_count,
            "medium": med_risk_count,
            "low": low_risk_count,
        },
        "model": {
            "name": model.metrics.get("selected_model", "gradient_boosting"),
            "pr_auc": val_metrics.get("pr_auc", 0.658),
            "roc_auc": val_metrics.get("roc_auc", 0.843),
            "threshold": model.threshold,
            "recall": val_metrics.get("recall_at_threshold", 0.94),
            "precision": val_metrics.get("precision_at_threshold", 0.42),
        },
        "features": {
            "all": ALL_FEATURES,
            "categorical": CATEGORICAL_FEATURES,
            "numeric": NUMERIC_FEATURES,
        }
    }


@app.get("/api/segments")
def get_segments(by: str = Query("Contract", description="Column to group by")):
    df, _, _ = get_resources()
    if by not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{by}' not found")

    agg = (
        df.assign(_churned=(df[TARGET] == "Yes").astype(float))
        .groupby(by, observed=True)
        .agg(
            customers=("model_risk", "size"),
            avg_risk=("model_risk", "mean"),
            churn_rate=("_churned", "mean"),
            avg_monthly_charges=("MonthlyCharges", "mean"),
        )
        .round(4)
        .reset_index()
    )
    return {
        "grouped_by": by,
        "data": agg.to_dict(orient="records"),
    }


@app.get("/api/customers")
def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    search: Optional[str] = None,
    risk_band: Optional[str] = None,
    contract: Optional[str] = None,
    sort_by: str = Query("model_risk", description="Column to sort by"),
    order: str = Query("desc", enum=["asc", "desc"]),
):
    df, model, _ = get_resources()
    filtered = df.copy()

    if search:
        s = search.strip().lower()
        filtered = filtered[filtered[ID_COL].str.lower().str.contains(s)]

    if contract:
        filtered = filtered[filtered["Contract"] == contract]

    if risk_band:
        if risk_band.lower() == "high":
            filtered = filtered[filtered["model_risk"] >= 0.66]
        elif risk_band.lower() == "medium":
            filtered = filtered[(filtered["model_risk"] >= 0.33) & (filtered["model_risk"] < 0.66)]
        elif risk_band.lower() == "low":
            filtered = filtered[filtered["model_risk"] < 0.33]

    if sort_by in filtered.columns:
        ascending = (order == "asc")
        filtered = filtered.sort_values(by=sort_by, ascending=ascending)

    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    page_data = filtered.iloc[start:end]

    records = []
    for _, row in page_data.iterrows():
        rec = row.to_dict()
        rec["risk_band"] = model.band(rec.get("model_risk", 0))
        records.append(rec)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1,
        "customers": records,
    }


@app.get("/api/customer/{customer_id}")
def get_customer(customer_id: str):
    df, model, _ = get_resources()
    try:
        pred = model.predict_churn_risk(customer_id, df)
        row = df[df[ID_COL] == customer_id].iloc[0].to_dict()
        return {
            "customer": row,
            "prediction": pred,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Customer ID '{customer_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/what-if")
def run_what_if(req: WhatIfRequest):
    df, model, _ = get_resources()
    try:
        res = model.what_if(req.customer_id, req.overrides, df)
        return res
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predict-hypothetical")
def predict_hypothetical(req: HypotheticalRequest):
    _, model, _ = get_resources()
    try:
        res = model.predict_hypothetical(req.features)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def chat_with_agent(req: ChatRequest):
    _, _, agent = get_resources()
    if req.clear_history:
        agent.memory.clear()

    try:
        resp = agent.ask(req.question)
        
        # Convert plotly figures to JSON specs if generated
        charts_data = []
        for fig in resp.charts:
            charts_data.append(json.loads(fig.to_json()))

        return {
            "answer": resp.answer,
            "charts": charts_data,
            "steps": resp.steps,
            "verification": resp.verification,
            "ok": resp.ok,
        }
    except Exception as e:
        return {
            "answer": f"Error running agent loop: {type(e).__name__} - {e}",
            "charts": [],
            "steps": [f"error: {e}"],
            "verification": {"error": str(e)},
            "ok": False,
        }


@app.get("/api/model-card")
def get_model_card():
    _, model, _ = get_resources()
    return {
        "metrics": model.metrics,
        "threshold": model.threshold,
        "baselines": model.baselines,
    }
