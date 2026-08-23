import numpy as np
import pytest


def test_predict_churn_risk_contract(model, df):
    out = model.predict_churn_risk("3668-QPYBK", df)
    assert set(out) >= {"customer_id", "risk_score", "risk_band", "top_factors"}
    assert 0.0 <= out["risk_score"] <= 1.0
    assert 1 <= len(out["top_factors"]) <= 5
    assert all({"feature", "value", "impact"} <= set(f) for f in out["top_factors"])


def test_unknown_customer_raises(model, df):
    with pytest.raises(KeyError):
        model.predict_churn_risk("0000-NOPE", df)


def test_what_if_two_year_contract_lowers_risk(model, df):
    """Domain sanity: locking a month-to-month churner into a 2-year contract
    should not raise their modelled risk."""
    out = model.what_if("3668-QPYBK", {"Contract": "Two year"}, df)
    assert out["projected_risk"] <= out["current_risk"]


def test_hypothetical_fills_defaults_and_validates(model):
    out = model.predict_hypothetical({"tenure": 1, "Contract": "Month-to-month"})
    assert 0.0 <= out["risk_score"] <= 1.0
    assert "gender" in out["defaults_used"]
    with pytest.raises(ValueError):
        model.predict_hypothetical({"NotAColumn": 1})
    with pytest.raises(ValueError):
        model.predict_hypothetical({"tenure": -5})


def test_scores_discriminate(model, df):
    """Model sanity on the training frame: churners should score higher on
    average than non-churners by a clear margin."""
    scores = model.score_frame(df)
    churned = scores[(df["Churn"] == "Yes").to_numpy()]
    stayed = scores[(df["Churn"] == "No").to_numpy()]
    assert churned.mean() > stayed.mean() + 0.15
    assert np.all((scores >= 0) & (scores <= 1))
