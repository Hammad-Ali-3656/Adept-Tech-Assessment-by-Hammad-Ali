import pandas as pd

from src.data_prep import clean, load_raw, model_frame


def test_totalcharges_numeric_and_imputed(df):
    assert pd.api.types.is_float_dtype(df["TotalCharges"])
    assert df["TotalCharges"].isna().sum() == 0
    new = df[df["NewCustomer"] == "Yes"]
    assert len(new) == 11
    assert (new["tenure"] == 0).all()
    assert (new["TotalCharges"] == 0.0).all()


def test_senior_citizen_recoded(df):
    assert set(df["SeniorCitizen"].unique()) == {"Yes", "No"}


def test_no_duplicate_ids(df):
    assert df["customerID"].is_unique


def test_model_frame_collapses_redundant_levels(df):
    dfm = model_frame(df)
    assert "No internet service" not in dfm["OnlineSecurity"].unique()
    assert "No phone service" not in dfm["MultipleLines"].unique()
    # analytics frame keeps the original levels for EDA
    assert "No internet service" in df["OnlineSecurity"].unique()


def test_clean_is_idempotent():
    once = clean(load_raw())
    twice = clean(once)
    pd.testing.assert_frame_equal(once, twice)
