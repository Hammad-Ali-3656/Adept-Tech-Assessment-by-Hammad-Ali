"""Churn model: training, persistence, and a clean callable interface.

The public surface the agent (and anything else) uses:

    model = ChurnModel.load()
    model.predict_churn_risk("7590-VHVEG")
    -> {"customer_id": ..., "risk_score": 0.63, "risk_band": "High",
        "top_factors": [{"feature": "Contract", "value": "Month-to-month",
                          "impact": +0.21}, ...]}

    model.predict_hypothetical({"tenure": 2, "Contract": "Month-to-month", ...})
    model.what_if("7590-VHVEG", {"Contract": "Two year"})
    model.score_frame(df)   # vectorised scores for segment aggregation

Metric choice (full argument in the README/notebook): the dataset is
imbalanced (26.5% churn) and the business cost is asymmetric — missing a
real churner costs a customer's lifetime value, while a false alarm costs
a cheap retention offer. Accuracy is therefore misleading (74% by always
predicting "No"). We select models on **PR-AUC (average precision)** —
it evaluates ranking quality specifically on the rare positive class —
and report ROC-AUC alongside for comparability. The operating threshold
is chosen to maximise **F2** (recall weighted 2x over precision) on a
held-out validation split, matching that cost asymmetry.

Per-customer "top factors" are model-agnostic local attributions: each
feature is replaced by its dataset baseline (mode / median) and the drop
in predicted risk is the feature's impact. Simple, honest, and doesn't
pretend to be SHAP.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
try:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (average_precision_score, fbeta_score,
                                 precision_score, recall_score, roc_auc_score)
    from sklearn.model_selection import (StratifiedKFold, cross_val_score,
                                         train_test_split)
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    ColumnTransformer = None
    Pipeline = None


try:
    import onnxruntime as rt
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    rt = None


class ONNXPipeline:
    """Official ONNX Runtime inference engine for production real-time predictions."""
    def __init__(self, onnx_path: str):
        if not HAS_ONNX:
            raise ImportError("onnxruntime is required to run ONNXPipeline. Install with pip install onnxruntime")
        # Run using CPUExecutionProvider
        self.session = rt.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.output_names = [out.name for out in self.session.get_outputs()]

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        feed = {}
        for feat in ALL_FEATURES:
            if feat in NUMERIC_FEATURES:
                feed[feat] = df[feat].values.astype(np.float32).reshape(-1, 1)
            else:
                feed[feat] = df[feat].astype(str).values.reshape(-1, 1)
        
        outputs = self.session.run(None, feed)
        probs = outputs[1]
        if isinstance(probs, list) and isinstance(probs[0], dict):
            # Dict zipmap output format
            arr = np.array([[row[0], row[1]] for row in probs], dtype=np.float32)
            return arr
        elif isinstance(probs, np.ndarray) and probs.ndim == 2:
            return probs
        elif isinstance(probs, np.ndarray) and probs.ndim == 1:
            return np.column_stack([1.0 - probs, probs])
        return np.array(probs, dtype=np.float32)



from .. import config
from ..data_prep import (ALL_FEATURES, CATEGORICAL_FEATURES, ID_COL,
                         NUMERIC_FEATURES, TARGET, load_clean, model_frame)

RANDOM_STATE = 42
RISK_BANDS = [(0.66, "High"), (0.33, "Medium"), (0.0, "Low")]


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ("num", StandardScaler(), NUMERIC_FEATURES),
    ])


def candidate_models() -> dict:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", C=1.0),
        "random_forest": RandomForestClassifier(
            n_estimators=400, min_samples_leaf=4, class_weight="balanced",
            random_state=RANDOM_STATE, n_jobs=-1),
        "gradient_boosting": GradientBoostingClassifier(
            random_state=RANDOM_STATE),
    }


@dataclass
class ChurnModel:
    pipeline: Pipeline
    threshold: float
    baselines: dict                     # feature -> mode/median for attributions
    metrics: dict = field(default_factory=dict)
    reference_ids: list = field(default_factory=list)

    # ---------- training ----------
    @classmethod
    def train(cls, df_clean: pd.DataFrame | None = None, verbose: bool = True) -> "ChurnModel":
        df_clean = df_clean if df_clean is not None else load_clean()
        dfm = model_frame(df_clean)
        X, y = dfm[ALL_FEATURES], (dfm[TARGET] == "Yes").astype(int)

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE)

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        selection = {}
        for name, est in candidate_models().items():
            pipe = Pipeline([("prep", _preprocessor()), ("clf", est)])
            ap = cross_val_score(pipe, X_train, y_train, cv=cv,
                                 scoring="average_precision", n_jobs=-1)
            roc = cross_val_score(pipe, X_train, y_train, cv=cv,
                                  scoring="roc_auc", n_jobs=-1)
            selection[name] = {"pr_auc_cv": float(ap.mean()),
                               "pr_auc_cv_std": float(ap.std()),
                               "roc_auc_cv": float(roc.mean())}
            if verbose:
                print(f"{name:22s} PR-AUC {ap.mean():.4f}±{ap.std():.4f}  "
                      f"ROC-AUC {roc.mean():.4f}")

        best_name = max(selection, key=lambda n: selection[n]["pr_auc_cv"])
        pipe = Pipeline([("prep", _preprocessor()),
                         ("clf", candidate_models()[best_name])])
        pipe.fit(X_train, y_train)

        # threshold: maximise F2 on the held-out validation split
        val_proba = pipe.predict_proba(X_val)[:, 1]
        grid = np.linspace(0.05, 0.95, 181)
        f2 = [fbeta_score(y_val, val_proba >= t, beta=2) for t in grid]
        threshold = float(grid[int(np.argmax(f2))])

        preds = val_proba >= threshold
        metrics = {
            "selected_model": best_name,
            "candidates_cv": selection,
            "validation": {
                "pr_auc": float(average_precision_score(y_val, val_proba)),
                "roc_auc": float(roc_auc_score(y_val, val_proba)),
                "threshold": threshold,
                "recall_at_threshold": float(recall_score(y_val, preds)),
                "precision_at_threshold": float(precision_score(y_val, preds)),
                "f2_at_threshold": float(max(f2)),
                "churn_base_rate": float(y.mean()),
            },
        }

        # refit on ALL data for the deployed artifact
        pipe_full = Pipeline([("prep", _preprocessor()),
                              ("clf", candidate_models()[best_name])])
        pipe_full.fit(X, y)

        baselines = {c: dfm[c].mode().iloc[0] for c in CATEGORICAL_FEATURES}
        baselines |= {c: float(dfm[c].median()) for c in NUMERIC_FEATURES}

        return cls(pipeline=pipe_full, threshold=threshold,
                   baselines=baselines, metrics=metrics,
                   reference_ids=dfm[ID_COL].tolist())

    def save(self, path=None) -> None:
        path = path or config.MODEL_PATH
        config.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        config.MODEL_CARD_PATH.write_text(json.dumps(self.metrics, indent=2))

    @classmethod
    def load(cls, path=None) -> "ChurnModel":
        from pathlib import Path
        onnx_file = config.ARTIFACT_DIR / "churn_model.onnx"
        meta_file = config.ARTIFACT_DIR / "churn_model_onnx_meta.json"

        # 1. Load official ONNX model pipeline if available
        if onnx_file.exists() and meta_file.exists() and HAS_ONNX:
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                pipe = ONNXPipeline(str(onnx_file))
                return cls(
                    pipeline=pipe,
                    threshold=meta["threshold"],
                    baselines=meta["baselines"],
                    metrics=meta["metrics"],
                    reference_ids=meta["reference_ids"],
                )
            except Exception as e:
                pass

        # 2. Fallback to standard joblib model
        return joblib.load(path or config.MODEL_PATH)

    # ---------- inference ----------
    def _frame_for(self, rows: pd.DataFrame) -> pd.DataFrame:
        return model_frame(rows)[ALL_FEATURES]

    def score_frame(self, df_clean_rows: pd.DataFrame) -> np.ndarray:
        """Vectorised churn probabilities for cleaned rows."""
        return self.pipeline.predict_proba(self._frame_for(df_clean_rows))[:, 1]

    @staticmethod
    def band(score: float) -> str:
        for cut, name in RISK_BANDS:
            if score >= cut:
                return name
        return "Low"

    def _row_for_customer(self, df_clean: pd.DataFrame, customer_id: str) -> pd.DataFrame:
        row = df_clean[df_clean[ID_COL] == customer_id]
        if row.empty:
            raise KeyError(f"customer_id {customer_id!r} not found in dataset")
        return row

    def _validate_features(self, features: dict) -> dict:
        """Fill a hypothetical customer from baselines; reject unknown keys."""
        unknown = set(features) - set(ALL_FEATURES)
        if unknown:
            raise ValueError(f"unknown feature(s): {sorted(unknown)}; "
                             f"valid features: {ALL_FEATURES}")
        filled = dict(self.baselines)
        filled.update(features)
        for c in NUMERIC_FEATURES:
            filled[c] = float(filled[c])
            if filled[c] < 0:
                raise ValueError(f"{c} cannot be negative")
        return filled

    def _top_factors(self, row: pd.DataFrame, k: int = 5) -> list[dict]:
        """Baseline-substitution local attribution (model-agnostic)."""
        base_score = float(self.score_frame(row)[0])
        impacts = []
        for feat in ALL_FEATURES:
            counter = row.copy()
            counter[feat] = self.baselines[feat]
            if counter[feat].iloc[0] == row[feat].iloc[0]:
                continue
            delta = base_score - float(self.score_frame(counter)[0])
            impacts.append({
                "feature": feat,
                "value": row[feat].iloc[0] if feat not in NUMERIC_FEATURES
                         else float(row[feat].iloc[0]),
                "impact": round(delta, 4),
            })
        impacts.sort(key=lambda d: abs(d["impact"]), reverse=True)
        return impacts[:k]

    def predict_churn_risk(self, customer_id: str,
                           df_clean: pd.DataFrame | None = None) -> dict:
        """The Stage-1 contract: predict_churn_risk(id) -> {risk_score, top_factors}."""
        df_clean = df_clean if df_clean is not None else load_clean()
        row = self._row_for_customer(df_clean, customer_id)
        score = float(self.score_frame(row)[0])
        return {
            "customer_id": customer_id,
            "risk_score": round(score, 4),
            "risk_band": self.band(score),
            "would_flag_as_churn": bool(score >= self.threshold),
            "decision_threshold": self.threshold,
            "top_factors": self._top_factors(row),
        }

    def predict_hypothetical(self, features: dict) -> dict:
        filled = self._validate_features(features)
        row = pd.DataFrame([filled])[ALL_FEATURES]
        score = float(self.pipeline.predict_proba(row)[0, 1])
        return {
            "hypothetical_features": filled,
            "defaults_used": sorted(set(ALL_FEATURES) - set(features)),
            "risk_score": round(score, 4),
            "risk_band": self.band(score),
            "would_flag_as_churn": bool(score >= self.threshold),
        }

    def what_if(self, customer_id: str, overrides: dict,
                df_clean: pd.DataFrame | None = None) -> dict:
        """Current risk vs projected risk under changed feature conditions."""
        df_clean = df_clean if df_clean is not None else load_clean()
        row = self._row_for_customer(df_clean, customer_id)
        unknown = set(overrides) - set(ALL_FEATURES)
        if unknown:
            raise ValueError(f"unknown feature(s): {sorted(unknown)}")
        current = float(self.score_frame(row)[0])
        counter = row.copy()
        for k, v in overrides.items():
            counter[k] = float(v) if k in NUMERIC_FEATURES else v
        projected = float(self.score_frame(counter)[0])
        return {
            "customer_id": customer_id,
            "current_risk": round(current, 4),
            "projected_risk": round(projected, 4),
            "delta": round(projected - current, 4),
            "overrides": overrides,
            "current_band": self.band(current),
            "projected_band": self.band(projected),
        }


def train_and_save(verbose: bool = True) -> ChurnModel:
    model = ChurnModel.train(verbose=verbose)
    model.save()
    return model
