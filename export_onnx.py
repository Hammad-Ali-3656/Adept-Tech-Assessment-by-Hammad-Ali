"""Export trained scikit-learn pipeline to ONNX format."""
import json
import joblib
import numpy as np
import pandas as pd
from src.data_prep import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, load_clean, model_frame
from src.model.churn_model import ChurnModel

print("Loading existing joblib model...")
m = ChurnModel.load()
pipe = m.pipeline

print("Pipeline clf:", pipe.named_steps["clf"])

# Convert using skl2onnx or custom lightweight ONNX export
try:
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType, StringTensorType, Int64TensorType
    import onnxruntime as rt

    # Define input types
    initial_type = []
    df = model_frame(load_clean())[ALL_FEATURES]
    for col in ALL_FEATURES:
        if col in NUMERIC_FEATURES:
            initial_type.append((col, FloatTensorType([None, 1])))
        else:
            initial_type.append((col, StringTensorType([None, 1])))

    onx = convert_sklearn(pipe, initial_types=initial_type, target_opset=12)
    with open("artifacts/churn_model.onnx", "wb") as f:
        f.write(onx.SerializeToString())
    print("ONNX model saved successfully to artifacts/churn_model.onnx!")
except Exception as e:
    print("skl2onnx error:", e)
