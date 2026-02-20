"""
Explainability module for antibiotic resistance prediction models.
Provides SHAP-based explanations for XGBoost and DNABERT models.
"""

from .shap_utils import SHAPUtils
from .xgboost_explainer import XGBoostExplainer
from .transformer_explainer import TransformerExplainer

__all__ = ['SHAPUtils', 'XGBoostExplainer', 'TransformerExplainer']
