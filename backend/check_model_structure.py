"""
Check the actual structure of the XGBoost model.
"""
import pickle
import numpy as np
from pathlib import Path

# Load model
model_path = Path("trained_models/xgboost_f0849bdd.pkl")
with open(model_path, 'rb') as f:
    model_dict = pickle.load(f)

print("Model structure:")
for key, value in model_dict.items():
    if key == 'models':
        print(f"\n{key}:")
        if isinstance(value, dict):
            for antibiotic, model in value.items():
                print(f"  - {antibiotic}: {type(model)}")
                if hasattr(model, 'n_features_in_'):
                    print(f"    Features: {model.n_features_in_}")
                if hasattr(model, 'feature_names_in_'):
                    print(f"    Feature names: {len(model.feature_names_in_)}")
        else:
            print(f"  Type: {type(value)}")
    elif key == 'feature_names':
        print(f"\n{key}: {len(value)} items")
        print(f"  First 5: {value[:5]}")
    elif key == 'antibiotic_names':
        print(f"\n{key}: {len(value)} items")
        print(f"  First 5: {value[:5]}")
    elif key == 'label_inv_mappings':
        print(f"\n{key}:")
        for antibiotic, mapping in value.items():
            print(f"  - {antibiotic}: {len(mapping)} classes")
    elif key == 'hyperparameters':
        print(f"\n{key}:")
        for param, val in value.items():
            print(f"  - {param}: {val}")
    else:
        print(f"\n{key}: {type(value)}")
