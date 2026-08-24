"""Convert Scikit-Learn Pipeline to official ONNX format and verify parity."""
import json
import joblib
import numpy as np
import pandas as pd
import onnxruntime as rt
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType, StringTensorType, Int64TensorType
from src.data_prep import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, TARGET, ID_COL, load_clean, model_frame

print("1. Loading trained model from artifacts/churn_model.joblib...")
model_obj = joblib.load("artifacts/churn_model.joblib")
pipe = model_obj.pipeline

df_clean = load_clean()
dfm = model_frame(df_clean)
X_sample = dfm[ALL_FEATURES]

# Define typed inputs for each feature
initial_types = []
for feat in ALL_FEATURES:
    if feat in NUMERIC_FEATURES:
        initial_types.append((feat, FloatTensorType([None, 1])))
    else:
        initial_types.append((feat, StringTensorType([None, 1])))

print("2. Converting pipeline to ONNX format...")
# Target opset 12 or 14 for maximum compatibility
onx = convert_sklearn(pipe, initial_types=initial_types, target_opset=12,
                      options={type(pipe.named_steps["clf"]): {"zipmap": False}})

onnx_path = "artifacts/churn_model.onnx"
with open(onnx_path, "wb") as f:
    f.write(onx.SerializeToString())

print(f"   -> Successfully saved ONNX model to {onnx_path}!")

# Save metadata (threshold, baselines, metrics)
meta = {
    "threshold": model_obj.threshold,
    "baselines": model_obj.baselines,
    "metrics": model_obj.metrics,
    "reference_ids": model_obj.reference_ids,
}
with open("artifacts/churn_model_onnx_meta.json", "w") as f:
    json.dump(meta, f, indent=2)
print("   -> Successfully saved ONNX metadata to artifacts/churn_model_onnx_meta.json!")

print("3. Verifying ONNX Runtime inference parity...")
sess = rt.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])

def prepare_onnx_inputs(df: pd.DataFrame):
    feed = {}
    for feat in ALL_FEATURES:
        if feat in NUMERIC_FEATURES:
            feed[feat] = df[feat].values.astype(np.float32).reshape(-1, 1)
        else:
            feed[feat] = df[feat].astype(str).values.reshape(-1, 1)
    return feed

test_subset = X_sample.head(50)
feed_dict = prepare_onnx_inputs(test_subset)

# ONNX inference
onnx_outputs = sess.run(None, feed_dict)
# Output probabilities are usually in output index 1
onnx_probs = onnx_outputs[1][:, 1]

# Sklearn inference
sklearn_probs = pipe.predict_proba(test_subset)[:, 1]

max_diff = np.max(np.abs(sklearn_probs - onnx_probs))
print(f"   -> Max difference between Sklearn and ONNX Runtime: {max_diff:.8f}")
assert max_diff < 1e-4, f"Discrepancy too large: {max_diff}"
print("   -> ONNX PARITY CHECK 100% PASSED!")
