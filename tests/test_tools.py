from src.agent.tools import ToolBelt


def belt(df, model):
    return ToolBelt(df, model)


def test_segment_risk_by_contract(df, model):
    out = belt(df, model).segment_risk(group_by=["Contract"])
    assert out["ok"] and len(out["segments"]) == 3
    seg = {s["Contract"]: s for s in out["segments"]}
    # month-to-month must be the riskiest segment, by model and by actuals
    assert seg["Month-to-month"]["avg_model_risk"] > seg["Two year"]["avg_model_risk"]
    assert seg["Month-to-month"]["actual_churn_rate"] > seg["Two year"]["actual_churn_rate"]
    assert sum(s["customers"] for s in out["segments"]) == len(df)


def test_segment_risk_bad_inputs(df, model):
    b = belt(df, model)
    assert not b.segment_risk(group_by=["NoCol"])["ok"]
    assert not b.segment_risk(filter_query="Contract == 'Nope'")["ok"]
    assert not b.segment_risk(filter_query="bad !!! query")["ok"]


def test_data_summary_aspects(df, model):
    b = belt(df, model)
    assert b.data_summary("schema")["rows"] == 7043
    assert b.data_summary("value_counts", "Contract")["ok"]
    cr = b.data_summary("churn_rate_by", "Contract")
    assert cr["ok"] and len(cr["churn_rate_by"]) == 3
    assert not b.data_summary("value_counts")["ok"]
    assert not b.data_summary("nonsense")["ok"]


def test_make_chart_bar_churn_rate(df, model):
    b = belt(df, model)
    out = b.make_chart(kind="bar", x="Contract", y="churn_rate")
    assert out["ok"] and len(b.charts) == 1
    assert "aggregated_data" in out  # numbers are traceable evidence


def test_make_chart_model_risk_and_errors(df, model):
    b = belt(df, model)
    assert b.make_chart(kind="hist", x="model_risk")["ok"]
    assert not b.make_chart(kind="pie", x="Contract")["ok"]
    assert not b.make_chart(kind="bar", x="NoCol", y="churn_rate")["ok"]


def test_dispatch_records_trace_and_handles_bad_args(df, model):
    b = belt(df, model)
    out = b.dispatch("predict_churn", {"wrong_arg": 1})
    assert not out["ok"]
    out2 = b.dispatch("no_such_tool", {})
    assert not out2["ok"]
    assert len(b.trace) == 2
    assert "evidence" not in b.evidence_text() or b.evidence_text()
