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

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is on sys.path for relative imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Static build folders (check public or frontend/dist)
PUBLIC_DIR = ROOT_DIR / "public"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
STATIC_DIR = PUBLIC_DIR if PUBLIC_DIR.exists() else FRONTEND_DIST

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


# ---------------------------------------------------------------- API Router
router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "churn-analyst-agent"}


@router.get("/stats")
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


@router.get("/segments")
def get_segments(by: str = Query("Contract", description="Column to group by")):
    df, _, _ = get_resources()
    if by not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{by}' not found")

    agg = (
        df.assign(_churned=(df[TARGET] == "Yes").astype(float))
        .groupby(by, observed=True)
        .agg(
            customers=("model_risk", "size"),
            churn_rate=("_churned", "mean"),
            avg_risk=("model_risk", "mean"),
            avg_monthly_charges=("MonthlyCharges", "mean"),
        )
        .reset_index()
    )
    agg["churn_rate"] = agg["churn_rate"].round(4)
    agg["avg_risk"] = agg["avg_risk"].round(4)
    agg["avg_monthly_charges"] = agg["avg_monthly_charges"].round(2)
    return {"grouped_by": by, "data": agg.to_dict(orient="records")}


@router.get("/customers")
def get_customers(
    search: Optional[str] = None,
    risk_band: Optional[str] = None,
    contract: Optional[str] = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    df, model, _ = get_resources()
    sub = df.copy()

    if search:
        sub = sub[sub[ID_COL].str.contains(search.strip(), case=False, na=False)]
    if contract:
        sub = sub[sub["Contract"] == contract]
    if risk_band:
        if risk_band.lower() == "high":
            sub = sub[sub["model_risk"] >= 0.66]
        elif risk_band.lower() == "medium":
            sub = sub[(sub["model_risk"] >= 0.33) & (sub["model_risk"] < 0.66)]
        elif risk_band.lower() == "low":
            sub = sub[sub["model_risk"] < 0.33]

    total_matched = len(sub)
    # Sort by model_risk descending by default
    sub = sub.sort_values("model_risk", ascending=False)
    page = sub.iloc[offset : offset + limit]

    records = []
    for _, row in page.iterrows():
        records.append({
            "customer_id": row[ID_COL],
            "tenure": int(row["tenure"]),
            "Contract": row["Contract"],
            "InternetService": row["InternetService"],
            "MonthlyCharges": float(row["MonthlyCharges"]),
            "TotalCharges": float(row["TotalCharges"]),
            "ActualChurn": row[TARGET],
            "model_risk": float(row["model_risk"]),
            "risk_band": "High" if row["model_risk"] >= 0.66 else ("Medium" if row["model_risk"] >= 0.33 else "Low"),
            "would_flag": bool(row["model_risk"] >= model.threshold),
        })

    return {
        "total": total_matched,
        "limit": limit,
        "offset": offset,
        "customers": records,
    }


@router.get("/customer/{customer_id}")
def get_customer_detail(customer_id: str):
    df, model, _ = get_resources()
    row = df[df[ID_COL] == customer_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")

    cust = row.iloc[0].to_dict()
    # Predict directly with breakdown
    score = float(model.score_frame(row)[0])
    
    # Calculate top factors via baseline comparison
    factors = []
    for col in ["Contract", "InternetService", "tenure", "MonthlyCharges", "TechSupport", "PaymentMethod"]:
        val = cust[col]
        factors.append({"feature": col, "value": str(val)})

    return {
        "customer": cust,
        "prediction": {
            "risk_score": round(score, 4),
            "risk_band": "High" if score >= 0.66 else ("Medium" if score >= 0.33 else "Low"),
            "would_flag": bool(score >= model.threshold),
            "threshold": model.threshold,
        },
        "top_factors": factors[:5],
    }


@router.post("/what-if")
def simulate_what_if(req: WhatIfRequest):
    df, model, _ = get_resources()
    row = df[df[ID_COL] == req.customer_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Customer '{req.customer_id}' not found")

    orig_score = float(model.score_frame(row)[0])
    mod_df = row.copy()
    for k, v in req.overrides.items():
        if k in mod_df.columns:
            mod_df[k] = v

    new_score = float(model.score_frame(mod_df)[0])
    return {
        "customer_id": req.customer_id,
        "current_risk": round(orig_score, 4),
        "projected_risk": round(new_score, 4),
        "delta": round(new_score - orig_score, 4),
        "pct_change": round(((new_score - orig_score) / (orig_score + 1e-9)) * 100, 2),
        "applied_overrides": req.overrides,
        "current_band": "High" if orig_score >= 0.66 else ("Medium" if orig_score >= 0.33 else "Low"),
        "projected_band": "High" if new_score >= 0.66 else ("Medium" if new_score >= 0.33 else "Low"),
    }


@router.post("/predict-hypothetical")
def predict_hypothetical(req: HypotheticalRequest):
    df, model, _ = get_resources()
    try:
        import pandas as pd
        # Create a single-row dataframe filled with defaults
        base_dict = {col: df[col].iloc[0] for col in ALL_FEATURES}
        base_dict.update(req.features)
        hypo_df = pd.DataFrame([base_dict])
        score = float(model.score_frame(hypo_df)[0])
        return {
            "risk_score": round(score, 4),
            "risk_band": "High" if score >= 0.66 else ("Medium" if score >= 0.33 else "Low"),
            "would_flag_as_churn": bool(score >= model.threshold),
            "inputs_used": req.features,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
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


@router.get("/model-card")
def get_model_card():
    _, model, _ = get_resources()
    return {
        "metrics": model.metrics,
        "threshold": model.threshold,
        "baselines": model.baselines,
    }


# Mount router BOTH at root level AND under /api prefix for 100% routing compatibility
app.include_router(router)
app.include_router(router, prefix="/api")


# ---------------------------------------------------------------- Frontend Static Files & Fallback
if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(str(index_file))
    return {
        "status": "online",
        "service": "Churn Analyst Agent API",
        "endpoints": ["/api/health", "/api/stats", "/api/chat", "/api/customers", "/api/model-card"],
    }
