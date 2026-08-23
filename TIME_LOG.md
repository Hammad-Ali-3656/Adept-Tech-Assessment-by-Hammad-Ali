# Honest time log (~9.5 hours)

| Time | What |
|------|------|
| 0:45 | Read the brief, explored the dataset, found and verified the data issues (blank TotalCharges → tenure-0 pattern, encoding inconsistency, redundant levels) |
| 1:15 | Cleaning module + model: candidate comparison, PR-AUC/F2 metric reasoning, threshold selection, `predict_churn_risk` / `what_if` / `predict_hypothetical` interface, attribution method |
| 2:30 | Agent core: LLM client (cache/backoff/routing), sandbox (AST rules + escape testing), 7 tools, plan-act-check loop, JSON fallback, memory, guardrails, critic. The verification-retry flow went through two designs before the layered one stuck |
| 1:00 | Streamlit app: chat, trace expander, charts, error handling, missing-key path |
| 1:30 | Tests: 45 offline tests incl. MockLLM episodes; fixed 4 real bugs they caught (chart column validation, injection regex gap, non-idempotent cleaning on pandas 3, sandbox thread leak — the last one cost the most head-scratching) |
| 1:00 | Eval set: computed ground truths, built harness + mock plans, adversarial items, report generation |
| 1:00 | Executed notebook (EDA story, metric argument, threshold curves) |
| 0:30 | README, this file, reflection, Dockerfile, deploy notes, final verification pass |

**Where I stopped:** everything required is done and tested offline; the
live-LLM path is wired and key-ready but I stopped short of paid/live API
testing and the hosted deployment step (documented in the README). Next hour
would have gone to a `--live` eval run and Streamlit Cloud deployment.
