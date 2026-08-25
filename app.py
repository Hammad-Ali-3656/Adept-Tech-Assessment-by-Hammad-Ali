"""Streamlit chat UI for the churn analyst agent.

Run:  streamlit run app.py
"""
from __future__ import annotations

import traceback

import streamlit as st

from src import config
from src.agent import AnalystAgent
from src.agent.llm_client import LLMNotConfigured
from src.data_prep import load_clean
from src.model import ChurnModel

st.set_page_config(page_title="Churn Analyst Agent", page_icon="📉",
                   layout="wide")


# ---------------------------------------------------------------- resources
@st.cache_resource(show_spinner="Loading data + model…")
def load_resources():
    df = load_clean()
    onnx_file = config.ARTIFACT_DIR / "churn_model.onnx"
    if onnx_file.exists() or config.MODEL_PATH.exists():
        model = ChurnModel.load()
    else:
        with st.spinner("First run — training the churn model (~2 min)…"):
            from src.model import train_and_save
            model = train_and_save(verbose=False)
    return df, model



def get_agent() -> AnalystAgent:
    if "agent" not in st.session_state:
        df, model = load_resources()
        st.session_state.agent = AnalystAgent(df, model)
    return st.session_state.agent


# ---------------------------------------------------------------- sidebar
def sidebar(df, model):
    with st.sidebar:
        st.title("📉 Churn Analyst")
        st.caption("Autonomous data analyst over the Telco churn dataset "
                   "and a trained churn model.")

        if not config.api_key():
            st.error("No LLM API key set. Copy `.env.example` → `.env` and add "
                     "your free Groq or OpenRouter key, then restart.",
                     icon="🔑")

        st.subheader("Dataset at a glance")
        churn_rate = (df["Churn"] == "Yes").mean()
        c1, c2 = st.columns(2)
        c1.metric("Customers", f"{len(df):,}")
        c2.metric("Churn rate", f"{churn_rate:.1%}")
        v = model.metrics.get("validation", {})
        c1.metric("Model PR-AUC", f"{v.get('pr_auc', 0):.3f}")
        c2.metric("Model ROC-AUC", f"{v.get('roc_auc', 0):.3f}")
        st.caption(f"Model: {model.metrics.get('selected_model', '?')} · "
                   f"threshold {model.threshold:.3f} (F2-optimal)")

        with st.expander("Example questions"):
            st.markdown(
                "- Which customers are most likely to churn?\n"
                "- Does churn risk correlate with contract type?\n"
                "- Show monthly charges distribution for high-risk customers\n"
                "- What's the churn risk for customer 3668-QPYBK?\n"
                "- What if that customer switched to a two-year contract?\n"
                "- Average risk by InternetService and Contract\n"
                "- Score a new customer: tenure 2, month-to-month, fiber optic")

        with st.expander("How answers are verified"):
            st.markdown(
                "1. The agent plans and calls **tools** (pandas sandbox, "
                "model, chart builder) — it never answers from memory.\n"
                "2. A deterministic verifier checks every **number** in the "
                "answer traces to a computed result.\n"
                "3. A **critic model** re-reads question, evidence and draft; "
                "failures are sent back for a retry.\n"
                "4. Unverifiable answers ship with an explicit ⚠️ caution.")

        if st.button("🧹 Clear conversation"):
            st.session_state.pop("history", None)
            if "agent" in st.session_state:
                st.session_state.agent.memory.clear()
            st.rerun()


# ---------------------------------------------------------------- chat
def render_turn(turn):
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        for fig in turn.get("charts", []):
            st.plotly_chart(fig, use_container_width=True)
        if turn.get("steps"):
            with st.expander("🔍 Agent trace (plan → tools → checks)"):
                for s in turn["steps"]:
                    st.code(s, language=None)


def main():
    df, model = load_resources()
    sidebar(df, model)
    st.title("Ask about your customers")
    st.caption("Natural-language questions → real computation on the data "
               "and the churn model. Nothing is answered from memory.")

    history = st.session_state.setdefault("history", [])
    for turn in history:
        render_turn(turn)

    question = st.chat_input("e.g. Does churn risk correlate with contract type?")
    if not question:
        return

    history.append({"role": "user", "content": question})
    render_turn(history[-1])

    with st.chat_message("assistant"):
        try:
            with st.spinner("Planning → computing → verifying…"):
                resp = get_agent().ask(question)
            st.markdown(resp.answer)
            for fig in resp.charts:
                st.plotly_chart(fig, use_container_width=True)
            if resp.steps:
                with st.expander("🔍 Agent trace (plan → tools → checks)"):
                    for s in resp.steps:
                        st.code(s, language=None)
            history.append({"role": "assistant", "content": resp.answer,
                            "charts": resp.charts, "steps": resp.steps})
        except LLMNotConfigured as e:
            st.warning(str(e), icon="🔑")
        except Exception:
            st.error("Unexpected error — the details are below; try rephrasing "
                     "your question.", icon="⚠️")
            with st.expander("Error details"):
                st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
