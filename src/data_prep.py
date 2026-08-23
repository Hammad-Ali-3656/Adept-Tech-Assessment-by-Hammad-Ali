"""Data loading + cleaning for the Telco customer-churn dataset.

Issues found during EDA (see notebook / README for full detail):

1. ``TotalCharges`` is read as *text*, because 11 rows contain a single
   space instead of a number. All 11 have ``tenure == 0`` — they are
   brand-new customers who have not been billed yet. Fix: coerce to
   numeric and impute 0.0 for those rows (not the mean — the "missing"
   value has a real meaning: nothing billed yet). A ``NewCustomer`` flag
   is kept so the information isn't silently lost.
2. ``SeniorCitizen`` is encoded 0/1 while every other binary column is
   Yes/No. Fix: map to Yes/No for consistency (and nicer EDA answers).
3. Six service columns use the three-level value "No internet service"
   which is 100% redundant with ``InternetService == 'No'`` (same for
   "No phone service" / ``PhoneService``). For the *model* we collapse
   these to "No" to avoid duplicated information; the original values
   are kept in the cleaned analytics table because they are useful for
   EDA-style questions.
4. Class imbalance: 26.5% churn — handled at the modelling stage
   (class weights + metric choice), not by mutating the data.
5. No duplicate rows or duplicate customerIDs; category labels are
   internally consistent (no case/whitespace variants) — verified, not
   assumed.
"""
from __future__ import annotations

import pandas as pd

from . import config

TARGET = "Churn"
ID_COL = "customerID"

SERVICE_COLS_INTERNET = [
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies",
]
SERVICE_COL_PHONE = "MultipleLines"

CATEGORICAL_FEATURES = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "PhoneService",
    "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
    "Contract", "PaperlessBilling", "PaymentMethod",
]
NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]
ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def load_raw(path=None) -> pd.DataFrame:
    return pd.read_csv(path or config.DATA_RAW)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Return the cleaned analytics dataframe (documented decisions above)."""
    out = df.copy()

    # (1) TotalCharges: text -> numeric; blanks are unbilled new customers.
    tc = pd.to_numeric(out["TotalCharges"].astype(str).str.strip(), errors="coerce")
    if "NewCustomer" not in out.columns:  # keep clean() idempotent
        out["NewCustomer"] = ((tc.isna()) & (out["tenure"] == 0)).map(
            {True: "Yes", False: "No"})
    out["TotalCharges"] = tc.fillna(0.0)

    # (2) SeniorCitizen 0/1 -> Yes/No, consistent with every other flag.
    if pd.api.types.is_numeric_dtype(out["SeniorCitizen"]):
        out["SeniorCitizen"] = out["SeniorCitizen"].map({0: "No", 1: "Yes"})

    # (5) safety: strip whitespace on all string columns (idempotent).
    for c in out.columns:
        if pd.api.types.is_string_dtype(out[c]) or out[c].dtype == object:
            out[c] = out[c].str.strip()

    # sanity assertions — fail loudly rather than train on garbage
    assert out[ID_COL].is_unique, "duplicate customerIDs after cleaning"
    assert out["TotalCharges"].notna().all()
    assert set(out[TARGET].unique()) == {"Yes", "No"}
    return out


def model_frame(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Model view: collapse structurally-redundant three-level values (3)."""
    out = df_clean.copy()
    for c in SERVICE_COLS_INTERNET:
        out[c] = out[c].replace({"No internet service": "No"})
    out[SERVICE_COL_PHONE] = out[SERVICE_COL_PHONE].replace({"No phone service": "No"})
    return out


def load_clean(path=None) -> pd.DataFrame:
    """Load raw and clean in one call (what the app + tools use)."""
    return clean(load_raw(path))


def save_clean(df_clean: pd.DataFrame) -> None:
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(config.DATA_CLEAN, index=False)
