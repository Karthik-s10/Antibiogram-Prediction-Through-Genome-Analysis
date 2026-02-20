"""
Check which antibiotics are in the XGBoost model.
"""
import pickle
from pathlib import Path

# Load model
model_path = Path("trained_models/xgboost_f0849bdd.pkl")
with open(model_path, 'rb') as f:
    model_dict = pickle.load(f)

print("Available antibiotics in XGBoost model:")
for i, antibiotic in enumerate(model_dict.keys(), 1):
    print(f"  {i:2d}. {antibiotic}")

print(f"\nTotal: {len(model_dict)} antibiotics")
