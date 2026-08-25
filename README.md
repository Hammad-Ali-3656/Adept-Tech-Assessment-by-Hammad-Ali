# Churn Analyst Agent — Autonomous Retention AI

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel%20Deployment-6366f1?style=for-the-badge&logo=vercel&logoColor=white)](https://adept-tech-assessment-by-hammad-ali-three.vercel.app/)

[![Python](https://img.shields.io/badge/Python-3.12-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61dafb?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![ONNX Runtime](https://img.shields.io/badge/Inference-ONNX%20Runtime-005ced?style=for-the-badge&logo=onnx&logoColor=white)](https://onnxruntime.ai/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/LLM%20Engine-Groq%20LPU-f55036?style=for-the-badge)](https://groq.com/)

An enterprise-grade **Autonomous Data Analyst & Churn Intelligence Platform** that investigates customer churn, executes real-time machine learning predictions via **ONNX Runtime**, conducts **What-If counterfactual simulations**, and answers natural-language business questions with a **zero-hallucination verification pipeline**.

---

### Live Production Application
**[https://adept-tech-assessment-by-hammad-ali-three.vercel.app/](https://adept-tech-assessment-by-hammad-ali-three.vercel.app/)**


---

## System Architecture

```
                                  USER INTERFACE
    ┌────────────────────────────────────────────────────────────────────────┐
    │  Modern React 18 + Vite SPA (Dashboard · AI Chat · What-If · Analytics) │
    └───────────────────────────────────┬────────────────────────────────────┘
                                        │ REST API (/api/*)
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                FastAPI Production Server (api/index.py)                │
    └──────┬────────────────────────────┬─────────────────────────────┬──────┘
           │                            │                             │
           ▼                            ▼                             ▼
    ┌──────────────┐             ┌──────────────┐              ┌──────────────┐
    │ ONNX Runtime │             │ Autonomous   │              │ Data & Stats │
    │  Inference   │             │ Analyst Loop │              │ Engine       │
    │ (sub-ms ML)  │             │ (ReAct Agent)│              │ (Pandas/EDA) │
    └──────────────┘             └───────┬──────┘              └──────────────┘
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           ▼                                                         ▼
  ┌──────────────────┐                                      ┌──────────────────┐
  │  Planner LLM     │                                      │  Critic & Verifier
  │  qwen/qwen3.6-27b│                                      │  openai/gpt-oss-20b
  │  (via Groq LPU)  │                                      │  (Deterministic) │
  └──────────────────┘                                      └──────────────────┘
```

---

## Core Features & Innovations

### 1. Autonomous ReAct Agent Loop
* **Multi-Step Tool Planning**: Decomposes complex queries (e.g. *"Which high-value customers with month-to-month contracts are most likely to churn and what retention strategies should we deploy?"*) into structured tool calls.
* **Deterministic Tool Belt**:
  1. `predict_churn(customer_id)`: Model prediction with local factor attribution.
  2. `what_if(customer_id, overrides)`: Counterfactual scenario testing.
  3. `predict_hypothetical(features)`: Synthetic customer profile risk scoring.
  4. `segment_risk(filter_query, group_by)`: SQL-like segment aggregations.
  5. `run_python(code)`: Sandboxed, AST-validated pandas execution.
  6. `make_chart(...)`: Deterministic Plotly visualizations.
  7. `data_summary()`: Dataset-wide distributions and missingness analysis.
* **Multi-Turn Memory**: Rolling memory with fact compaction preserves context across conversational turns without blowing token budgets.

### 2. Sub-Millisecond Real-Time ONNX Inference
* Exported the complete Scikit-Learn pipeline (One-Hot Encoding + Standard Scaling + Gradient Boosting Classifier) into the standard **Open Neural Network Exchange (`.onnx`)** binary format (`artifacts/churn_model.onnx`).
* Powered by **`onnxruntime`** in C++ for cross-platform execution with zero Scikit-Learn/Scipy runtime overhead.

### 3. Dual-Layer Zero-Hallucination Guardrails
1. **Pre-LLM Input Guardrails**: Deterministic regex and token safety filters that block prompt injections, role-hijacking, and oversized inputs before spending tokens.
2. **Deterministic Number Verifier**: Every number quoted in the agent's prose is extracted and verified against deterministic tool outputs (including percentage/decimal equivalence and pairwise differences).
3. **Semantic LLM Critic**: Re-validates directional logic and evidence consistency before delivering the response.
4. **Secret Scrubbing**: Strips environment variables, keys, and tokens from all output streams.

### 4. Interactive What-If Scenario Simulator
* Allows retention managers to simulate intervention strategies (e.g. upgrading a customer from *Month-to-month* to *One year*, applying a *15% discount*, or adding *TechSupport*).
* Visualizes the immediate before-and-after churn probability shift in real time.

---

## Production Deployment Challenges & Engineering Solutions

Deploying a multi-model, full-stack AI analyst to a serverless edge environment (Vercel) presented several hard real-world engineering challenges. Here is how each was systematically diagnosed and solved:

### 1. Serverless Function Size Limits (500 MB / 225 MB) -> ONNX Compilation
* **Challenge**: Standard Python ML stacks (`scikit-learn` ~115 MB, `scipy` ~185 MB, `pandas`, `numpy`) exceeded Vercel's serverless function package limit (500 MB uncompressed, 225 MB optimized limit), causing build failures.
* **Solution**: Compiled the entire trained Scikit-Learn pipeline (categorical one-hot encodings, standard scalers, and gradient boosting decision trees) into the standardized **Open Neural Network Exchange (`.onnx`) format** (`artifacts/churn_model.onnx` — 58.5 KB). At runtime, inference is executed using **`onnxruntime`** (~20 MB C++ engine). This dropped total runtime dependencies from **535 MB -> ~95 MB**, ensuring instant builds and sub-millisecond scoring.

### 2. LLM XML Tool-Calling Dialects -> Dynamic Qwen XML Parser
* **Challenge**: `qwen/qwen3.6-27b` on Groq intermittently emitted function invocations formatted as Hermes/Qwen XML (`<tool_call><function=segment_risk><parameter=...></parameter></function></tool_call>`) rather than standard OpenAI-style JSON schemas, causing raw XML markup to leak into the UI.
* **Solution**: Implemented `_parse_xml_tool_calls()` in [`src/agent/loop.py`](src/agent/loop.py) to intercept and parse Qwen's XML format dynamically, execute the tool calls against real data, and feed results back into the conversation for seamless executive reporting.

### 3. Serverless 10-Second Timeouts (HTTP 504) -> 2-Turn ReAct Optimization
* **Challenge**: Complex strategic questions (e.g. *"What are insights using which I can save customers from churning?"*) triggered verbose Chain-of-Thought `<think>` tokens and multiple sequential tool turns, exceeding Vercel's 10-second serverless execution window and returning `HTTP 504 Gateway Timeout`.
* **Solution**: Streamlined ReAct execution to **2 turns** (Turn 1: parallel vectorized tool execution -> Turn 2: executive synthesis), stripped verbose reasoning blocks, and optimized deterministic validation to return full strategic insights in **~1.5–2.5 seconds**.

### 4. False Unverified Figures & Groq Rate Limits (HTTP 429) -> Whitelist & Retry Caps
* **Challenge**: When the model cited total dataset dimensions (`7,043` rows) or baseline threshold quartiles (`75%`, `33%`), the deterministic number verifier rejected them as uncomputed, triggering 10 consecutive retry loops and exhausting Groq's requests-per-minute quota (`HTTP 429`).
* **Solution**: Added dataset schema constants (`7043`, `11`, `1869`, `5174`, `0.105`, `33%`, `66%`, `75%`, `100%`) directly to `SCHEMA_CONSTANTS` in [`src/agent/guardrails.py`](src/agent/guardrails.py), and capped retry attempts (`MAX_CRITIC_RETRIES = 1`).

### 5. Out-of-Scope Math & Strict Domain Enforcement -> Pre-LLM Guardrail Interceptor
* **Challenge**: Users entering general arithmetic (e.g. `10+10-19*161`, `whatis5*5`) received calculated math answers rather than domain-focused churn analytics.
* **Solution**: Implemented a zero-latency pre-LLM regex interceptor in `guardrails.check_input` that catches arithmetic operations before spending tokens, immediately returning a polite domain scope reminder in 0 milliseconds.

---

## Dataset Issues Identified & Remediation

Identified during exploratory data analysis in [`notebooks/churn_eda_and_model.ipynb`](notebooks/churn_eda_and_model.ipynb):

| Issue | Observation | Engineering Remediation |
| :--- | :--- | :--- |
| **`TotalCharges` text parsing** | 11 rows contained whitespace instead of numeric values. All 11 had `tenure == 0`. | Coerced to numeric, imputed **0.0** (brand-new unbilled customers), and added a `NewCustomer` boolean flag. |
| **`SeniorCitizen` encoding** | Encoded as `0/1` whereas all other binary fields used `Yes/No`. | Harmonized to `Yes/No` across the analytics views. |
| **Redundant service categories** | `"No internet service"` across 6 columns was 100% redundant with `InternetService == 'No'`. | Collapsed to `"No"` for model encoding; preserved verbatim in analytics views. |
| **Class Imbalance** | 26.5% positive churn rate. | Handled via **cost-sensitive learning** and **F2-score threshold tuning** (preserving calibrated true probabilities). |

---

## Model Selection & Metric Rationale

* **Why PR-AUC instead of Accuracy/ROC-AUC?**
  * In a dataset with 26.5% churn, standard accuracy is misleading (73.5% baseline accuracy by predicting zero churn).
  * ROC-AUC is inflated by the true-negative majority class. **PR-AUC (Average Precision)** measures ranking quality specifically on actual churners.
* **F2-Optimal Operating Threshold**:
  * Churn retention is asymmetric: missing a churner costs customer lifetime value (~$1,500+), while a false alarm costs only a cheap retention offer (~$15).
  * The decision threshold ($\tau = 0.105$) was selected on a held-out validation set to **maximize the F2 score** (weighting recall 2× over precision).
* **Validation Performance**:
  * **Selected Model**: Gradient Boosting Classifier
  * **PR-AUC**: **0.665 (5-Fold CV) / 0.658 (Validation Holdout)**
  * **ROC-AUC**: **0.847 (5-Fold CV) / 0.843 (Validation Holdout)**
  * **Recall at Threshold**: **94.1%** of all true churners detected.

---

## Quick Start & Local Development

### 1. Prerequisites
* Python 3.12+
* Node.js 18+ & npm

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone https://github.com/Hammad-Ali-3656/Adept-Tech-Assessment-by-Hammad-Ali.git
cd Adept-Tech-Assessment-by-Hammad-Ali

# Setup Python Virtual Environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
# Open .env and add your GROQ_API_KEY
```

### 3. Run the Full-Stack Application
```bash
# Terminal 1: Start FastAPI Backend
python -m uvicorn api.index:app --reload --port 8000

# Terminal 2: Start React Vite Frontend
cd frontend
npm install
npm run dev
```
* **Frontend Web App**: `http://localhost:5173`
* **Backend API Docs (Swagger)**: `http://localhost:8000/docs`

---

## Testing & Automated Evals

Run the test suite (45 offline unit tests with scripted Mock LLMs):
```bash
# Run all unit tests
python -m pytest tests -v

# Run offline evaluation suite (0% hallucination verification)
python -m evals.run_evals --mock

# Run live LLM evaluation suite (requires GROQ_API_KEY)
python -m evals.run_evals --live
```

---

## Deployment Architecture (Vercel)

The application is deployed on Vercel as a **Unified Full-Stack Architecture**:
* **Frontend**: Compiled React 18 SPA served via Vercel's global CDN Edge (`frontend/dist`).
* **Backend**: Serverless Python FastAPI functions (`api/index.py`) using `onnxruntime` for lightweight runtime inference (<100MB footprint).
* **Routing**: Handled via [`vercel.json`](vercel.json) rewrites:
  * `/api/(.*)` -> `api/index.py`
  * `/(.*)` -> Static CDN SPA fallback.

---

## Author & Contributor

* **Author**: Hammad Ali
* **Email**: [hali.bscs22seecs@seecs.edu.pk](mailto:hali.bscs22seecs@seecs.edu.pk)
* **GitHub**: [@Hammad-Ali-3656](https://github.com/Hammad-Ali-3656)

---

## AI Disclosure

Developed with AI pair-programming assistance for rapid code drafting, test suite design, and documentation. All data engineering decisions, metric justifications, ONNX conversions, and verification guardrails were independently validated and verified.

