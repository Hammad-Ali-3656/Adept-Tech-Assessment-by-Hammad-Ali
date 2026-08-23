# Churn Analyst Agent — Autonomous Data Analyst

An agent that answers natural-language questions about a telco customer-churn
dataset and a churn model trained on it — by **computing real answers with
tools** (a sandboxed pandas executor, the model, a chart builder) and
**verifying every number** before it reaches the user.

```
User question
   │  input guardrails (injection / size — deterministic, pre-LLM)
   ▼
Planner LLM (Groq/OpenRouter, native tool-calling; JSON fallback)
   │  plans multi-step, calls tools, sees errors, self-corrects
   ▼
Tools: run_python (sandboxed pandas, incl. model_risk column)
       predict_churn · what_if · predict_hypothetical
       segment_risk · data_summary · make_chart (plotly)
   ▼
Draft answer
   │  1) deterministic verifier: every figure must trace to a tool result
   │  2) critic agent (small model): semantic check vs evidence
   │  fail → reason fed back to planner, retry (×2) → else ship with  flag
   ▼
Answer + charts + full agent trace (visible in the UI)
```

## Quick start

```bash
git clone <this repo> && cd churn-analyst-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # add your free Groq (or OpenRouter) key
python -m scripts.train       # ~2 min: cleans data, trains + saves the model
streamlit run app.py
```

Docker instead:

```bash
docker build -t churn-agent .
docker run --env-file .env -p 8501:8501 churn-agent
```

Tests and evals (no API key needed — a scripted MockLLM drives the real tools):

```bash
python -m pytest tests -q          # 45 tests
python -m evals.run_evals --mock   # accuracy + hallucination report
python -m evals.run_evals --live   # same, with real LLM planning (needs key)
```

## The data issues I found, and what I did

Nothing was labelled; this came out of the investigation in
[`notebooks/churn_eda_and_model.ipynb`](notebooks/churn_eda_and_model.ipynb):

1. **`TotalCharges` parses as text** — 11 rows contain a single space. All 11
   have `tenure == 0`: brand-new customers never billed. *Fix:* coerce numeric,
   impute **0** (the true amount billed — mean-imputation would invent ~$2.3k of
   spend), and keep a `NewCustomer` flag so the information isn't lost.
2. **`SeniorCitizen` encoded 0/1** while every other flag is Yes/No. *Fix:*
   recode to Yes/No for consistency (matters for an agent doing EDA in English).
3. **Structurally redundant levels** — `"No internet service"` in six service
   columns is perfectly determined by `InternetService == 'No'` (verified, and
   same for `"No phone service"`). *Fix:* collapsed to `"No"` in the model's
   view; kept verbatim in the analytics view the agent queries.
4. **Class imbalance** (26.5% churn) — not an error; handled by metric and
   threshold choice, not resampling (resampling would distort the calibrated
   probabilities we expose as "risk").
5. **Checked and clean:** no duplicate rows/IDs, consistent category labels, sane
   numeric ranges; `TotalCharges ≈ tenure × MonthlyCharges` for all but 2 rows
   (plausible plan changes; untouched).

## Why this metric

**PR-AUC (average precision) for model selection; F2-optimal threshold for the
binary flag.** Accuracy is meaningless at 26.5% positives (73.5% by predicting
"nobody churns"). ROC-AUC is reported but inflated by the easy majority class;
PR-AUC scores ranking quality *on the churners specifically* — what a retention
team consumes. The decision threshold maximises F2 because the cost structure is
asymmetric (missed churner = lost lifetime value; false alarm = cheap offer), and
that trade-off is stated rather than hidden behind a 0.5 default: at the chosen
threshold the model catches ~94% of churners at ~42% precision. If outreach were
expensive, re-tune to F1 — one line in `src/model/churn_model.py`.

Result: gradient boosting, **PR-AUC 0.665 (CV) / 0.658 (holdout), ROC-AUC 0.843**.

## How the agent plans, verifies, and retries

* **Multi-step planning** — the planner decomposes questions ("which customers
  are likely to churn *and does that correlate with region*") into sequential
  tool calls; results feed later steps. Steps are capped (`MAX_AGENT_STEPS=8`),
  and a step-budget exhaustion forces an honest "here's what I have" answer.
* **Real computation, not LLM guesses** — `run_python` executes AST-validated
  pandas against the dataframe (with a precomputed `model_risk` column), inside
  our own process: no imports, no dunder access, no file/network I/O, empty
  builtins except an allowlist, daemon-thread timeout, output caps. This is a
  best-effort jail against prompted misuse, not a hostile-code boundary — that
  honesty matters.
* **Self-check** — tool errors and empty results go *back into the loop*; the
  planner is prompted to correct itself (tested: `tests/test_agent_loop.py::
  test_tool_error_fed_back_for_self_correction`).
* **Never invent a number** — two layers, cheapest first:
  1. a **deterministic verifier** extracts every figure from the draft and
     requires it to appear in recorded tool output (rounding + percent/fraction
     equivalence). No LLM involved, so it cannot be sweet-talked.
  2. a **critic agent** on a small model re-reads question + evidence + draft
     for semantic faithfulness (directions, comparisons, relevance).
  Failures are fed back for up to 2 retries; if verification still fails the
  answer ships with an explicit caution rather than silent confidence.
* **Multi-turn memory** — recent turns pass verbatim; older turns compact into
  a rolling "facts established earlier" summary, so "now break that down by
  contract type" works without restating context.

## Inference optimisation (free-tier rate limits are part of the design)

* **LRU response cache** for temperature-0 calls — repeat questions, critic
  re-checks and eval reruns cost zero tokens.
* **Model routing** — the primary planner (e.g. `qwen/qwen3.6-27b` or `llama-3.3-70b`) handles multi-step tool planning; guardrail and critic checks run on a lightweight model (e.g. `openai/gpt-oss-20b` or `llama-3.1-8b`) to conserve rate limits.
* **Exponential backoff with jitter honouring `Retry-After`** on 429/5xx.
* **Token budgeting** — tool outputs truncated at 4k chars, long histories
  compacted, hard `max_tokens` caps per call, ≤4 tool calls per turn, ≤8 steps.
* **Deterministic pre-LLM guardrails** — injection attempts are refused before
  any tokens are spent.

## Safeguards

* **Input:** length cap, control-char stripping, prompt-injection patterns
  (instruction override, system-prompt/key extraction) → polite refusal.
* **Execution:** the sandbox above.
* **Output:** number verification + critic (above), and API-key-shaped strings /
  env-var names scrubbed from every answer.

## Evals

`evals/eval_set.json`: 14 questions with ground truth precomputed from the
cleaned data and seeded model — EDA facts, individual risk, what-if projections,
segment aggregates, plus two adversarial items (a nonexistent column that must
fail gracefully, and an injection that must be refused pre-LLM).
`python -m evals.run_evals --mock` scores accuracy and hallucination rate using
scripted plans over the **real** tools and the **real** verification stack
(current report: `evals/eval_report.md` — 14/14, 0% hallucination); `--live`
reruns with genuine LLM planning once a key is set.

## Repo layout

```
frontend/                 React + Vite frontend (Dashboard, AI Chat, What-If, Model Intelligence)
api/index.py              FastAPI REST backend (Vercel Serverless Function & local API)
vercel.json               Vercel routing & static build configuration
app.py                    Streamlit UI (alternative lightweight local interface)
src/config.py             env-driven settings
src/data_prep.py          cleaning decisions (documented in-code)
src/model/churn_model.py  training, selection, threshold, callable interface
src/agent/loop.py         plan-act-check loop + retry policy
src/agent/tools.py        the 7 tools + schemas
src/agent/sandbox.py      restricted pandas execution
src/agent/guardrails.py   input checks, number verifier, secret scrubbing
src/agent/critic.py       deterministic + small-model answer review
src/agent/memory.py       multi-turn memory with compaction
src/agent/llm_client.py   Groq/OpenRouter client: cache, backoff, MockLLM
notebooks/                executed EDA + model notebook (Colab-compatible)
evals/                    eval set, harness, current report
tests/                    45 tests (all offline; MockLLM drives the loop)
```

## Deploying to Vercel (Recommended)

1. Push this repo to GitHub:
   ```bash
   git push origin main
   ```
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → Import this repository (`Adept-Tech-Assessment-by-Hammad-Ali`).
3. In **Project Settings → Environment Variables**, add:
   * `GROQ_API_KEY` = `gsk_...` (your free Groq key)
   * `LLM_PROVIDER` = `groq`
   * `PLANNER_MODEL` = `qwen/qwen3.6-27b`
   * `SMALL_MODEL` = `openai/gpt-oss-20b`
4. Click **Deploy**. Vercel will automatically build the React Vite frontend and serve the FastAPI backend via Serverless Functions.

## Running Locally

### Option A: React (Vite) + FastAPI Full-Stack App
```bash
# Terminal 1 - Start FastAPI Backend:
python -m uvicorn api.index:app --reload --port 8000

# Terminal 2 - Start React Frontend:
cd frontend && npm install && npm run dev
# Opens at http://localhost:5173
```

### Option B: Streamlit Interface
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

## AI tool use disclosure

Built with advanced AI pair-programming for code drafting, test design, and architecture documentation. All data findings, metric arguments, architecture decisions, and verification designs were reviewed and verified — the point of the verify-everything design is that nothing rests on trusting an LLM, including the ones that helped build it.

