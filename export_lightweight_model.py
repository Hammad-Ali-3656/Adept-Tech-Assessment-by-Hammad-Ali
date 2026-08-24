"""Extract exact model weights/trees/preprocessor and verify 100% numerical parity."""
import json
import joblib
import numpy as np
import pandas as pd
from src.data_prep import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET, ID_COL, load_clean, model_frame

m = joblib.load("artifacts/churn_model.joblib")
pipe = m.pipeline
prep = pipe.named_steps["prep"]
clf = pipe.named_steps["clf"]

# 1. Extract OneHotEncoder categories
cat_trans = prep.named_transformers_["cat"]
categories = {feat: list(cats) for feat, cats in zip(CATEGORICAL_FEATURES, cat_trans.categories_)}

# 2. Extract StandardScaler mean & scale
num_trans = prep.named_transformers_["num"]
scaler = {
    "mean": list(num_trans.mean_),
    "scale": list(num_trans.scale_),
    "features": NUMERIC_FEATURES,
}

# 3. Model weights / structure
model_type = type(clf).__name__
print("Clf type:", model_type)

bundle = {
    "model_type": model_type,
    "categories": categories,
    "scaler": scaler,
    "threshold": m.threshold,
    "baselines": m.baselines,
    "metrics": m.metrics,
    "reference_ids": m.reference_ids,
}

if model_type == "LogisticRegression":
    bundle["coef"] = clf.coef_[0].tolist()
    bundle["intercept"] = float(clf.intercept_[0])
elif model_type == "GradientBoostingClassifier":
    # Extract trees
    trees = []
    for estimator in clf.estimators_.ravel():
        tree = estimator.tree_
        trees.append({
            "children_left": tree.children_left.tolist(),
            "children_right": tree.children_right.tolist(),
            "feature": tree.feature.tolist(),
            "threshold": tree.threshold.tolist(),
            "value": tree.value.ravel().tolist(),
        })
    bundle["trees"] = trees
    bundle["learning_rate"] = float(clf.learning_rate)
    bundle["init_value"] = float(clf.init_.prior) if hasattr(clf.init_, "prior") else 0.0
elif model_type == "RandomForestClassifier":
    trees = []
    for estimator in clf.estimators_:
        tree = estimator.tree_
        trees.append({
            "children_left": tree.children_left.tolist(),
            "children_right": tree.children_right.tolist(),
            "feature": tree.feature.tolist(),
            "threshold": tree.threshold.tolist(),
            "value": (tree.value[:, 0, :] / tree.value[:, 0, :].sum(axis=1, keepdims=True)).tolist(),
        })
    bundle["trees"] = trees

with open("artifacts/churn_model_lightweight.json", "w") as f:
    json.dump(bundle, f)

print("Saved artifacts/churn_model_lightweight.json (Size: ~", round(len(json.dumps(bundle))/1024, 1), "KB)")

# ----------------- PARITY TEST -----------------
class LightweightPredictor:
    def __init__(self, data):
        self.categories = data["categories"]
        self.scaler = data["scaler"]
        self.threshold = data["threshold"]
        self.model_type = data["model_type"]
        self.data = data

    def transform(self, df):
        rows = []
        for _, row in df.iterrows():
            encoded = []
            # Categorical one-hot
            for feat in CATEGORICAL_FEATURES:
                val = row.get(feat, None)
                cats = self.categories[feat]
                for c in cats:
                    encoded.append(1.0 if str(val) == str(c) else 0.0)
            # Numeric standard scale
            for i, feat in enumerate(NUMERIC_FEATURES):
                val = float(row.get(feat, self.scaler["mean"][i]))
                mean = self.scaler["mean"][i]
                scale = self.scaler["scale"][i]
                encoded.append((val - mean) / scale if scale != 0 else 0.0)
            rows.append(encoded)
        return np.array(rows, dtype=np.float32)

    def predict_proba(self, df):
        X = self.transform(df)
        if self.model_type == "LogisticRegression":
            coef = np.array(self.data["coef"])
            intercept = self.data["intercept"]
            z = X @ coef + intercept
            p1 = 1.0 / (1.0 + np.exp(-z))
        elif self.model_type == "GradientBoostingClassifier":
            raw = np.full(len(X), self.data["init_value"], dtype=np.float32)
            lr = self.data["learning_rate"]
            for t in self.data["trees"]:
                cl = np.array(t["children_left"])
                cr = np.array(t["children_right"])
                feat = np.array(t["feature"])
                thresh = np.array(t["threshold"])
                val = np.array(t["value"])
                # Evaluate tree for each sample
                node = np.zeros(len(X), dtype=int)
                for i in range(len(X)):
                    curr = 0
                    while cl[curr] != -1:
                        if X[i, feat[curr]] <= thresh[curr]:
                            curr = cl[curr]
                        else:
                            curr = cr[curr]
                    raw[i] += lr * val[curr]
            p1 = 1.0 / (1.0 + np.exp(-raw))
        return p1

pred = LightweightPredictor(bundle)
test_df = model_frame(load_clean()).head(100)
sk_probs = pipe.predict_proba(test_df[ALL_FEATURES])[:, 1]
lt_probs = pred.predict_proba(test_df[ALL_FEATURES])

max_diff = np.max(np.abs(sk_probs - lt_probs))
print(f"Max prediction difference across test samples: {max_diff:.8f}")
assert max_diff < 1e-4, f"Parity mismatch: {max_diff}"
print("PARITY TEST PASSED! Exact match with Scikit-Learn to < 0.0001 difference.")
