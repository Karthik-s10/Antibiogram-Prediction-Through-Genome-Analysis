"""
Model Explanation Service

Provides SHAP-based explanations for model predictions.
Handles both XGBoost and DNABERT models with attention visualization.
"""
import shap
import numpy as np
import pandas as pd
import joblib
import torch
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import logging
from .attention_service import AttentionVisualizer

logger = logging.getLogger(__name__)

class ModelExplainer:
    """Handles model explanation generation using SHAP and attention visualization."""
    
    def __init__(self, model_path: Union[str, Path], feature_names: List[str], 
                 class_names: List[str], model_type: str = "xgboost"):
        """
        Initialize the explainer with a trained model.
        
        Args:
            model_path: Path to the trained model file
            feature_names: List of feature names
            class_names: List of class names
            model_type: Type of model ('xgboost' or 'dnabert')
        """
        self.model_path = Path(model_path)
        self.feature_names = feature_names
        self.class_names = class_names
        self.model_type = model_type.lower()
        self.model = self._load_model()
        self.explainer = self._create_explainer()
        self.attention_visualizer = None
        
        if self.model_type == "dnabert":
            self.attention_visualizer = AttentionVisualizer(str(model_path))
        
    def _load_model(self):
        """Load the model from disk."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
        if self.model_path.suffix == '.pkl' or self.model_type == "xgboost":
            return joblib.load(self.model_path)
        elif self.model_type == "dnabert":
            from transformers import AutoModelForSequenceClassification
            return AutoModelForSequenceClassification.from_pretrained(str(self.model_path))
        
    def _create_explainer(self):
        """Create appropriate SHAP explainer based on model type."""
        if hasattr(self.model, 'predict_proba'):  # Scikit-learn style
            return shap.TreeExplainer(self.model)
        elif hasattr(self.model, 'parameters'):  # PyTorch model
            return shap.DeepExplainer(self.model, torch.zeros(1, len(self.feature_names)))
        else:
            raise ValueError("Unsupported model type for SHAP explanation")
    
    def _get_shap_explanation(self, X_sample: Union[pd.DataFrame, np.ndarray, List[float]]) -> Dict:
        """
        Generate SHAP explanations for the given sample.
        
        Args:
            X_sample: Input data sample (single sample)
            
        Returns:
            Dictionary containing SHAP explanation data
        """
        if isinstance(X_sample, list):
            X_sample = np.array([X_sample])
        if not isinstance(X_sample, (pd.DataFrame, np.ndarray)):
            raise ValueError("Input must be a DataFrame, numpy array, or list")
            
        if isinstance(X_sample, np.ndarray) and len(X_sample.shape) == 1:
            X_sample = X_sample.reshape(1, -1)
            
        # Get SHAP values
        try:
            if hasattr(self.model, 'predict_proba'):
                shap_values = self.explainer.shap_values(X_sample)
                base_value = float(self.explainer.expected_value)
            else:
                # For PyTorch models
                shap_values = self.explainer.shap_values(X_sample)[0]
                base_value = 0.0  # PyTorch models might not have base value
                
            # Convert to list for JSON serialization
            if isinstance(shap_values, list):
                shap_values = [v.tolist() for v in shap_values]
            else:
                shap_values = shap_values.tolist()
                
            return {
                'shap_values': shap_values,
                'base_value': base_value,
                'feature_names': self.feature_names,
                'class_names': self.class_names,
                'sample': X_sample[0].tolist() if hasattr(X_sample[0], 'tolist') else X_sample[0]
            }
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            raise RuntimeError(f"Failed to generate explanation: {str(e)}")

    def explain(self, X_sample: Union[pd.DataFrame, np.ndarray, List[float]], 
               sequence: Optional[str] = None) -> Dict:
        """
        Generate explanations for the given sample.
        
        Args:
            X_sample: Input data sample
            sequence: Original DNA sequence (for attention visualization)
            
        Returns:
            Dictionary containing explanation data
        """
        explanation = {
            'shap': self._get_shap_explanation(X_sample),
            'attention': None
        }
        
        # Add attention visualization if sequence is provided and model is DNABERT
        if sequence and self.attention_visualizer:
            explanation['attention'] = self.attention_visualizer.get_attention(sequence)
            
        return explanation

    @classmethod
    def get_feature_importance(cls, explanation: Dict, class_idx: int = 0) -> List[Dict]:
        """Extract feature importance from SHAP explanation."""
        if 'shap' not in explanation:
            return []
            
        shap_values = explanation['shap']['shap_values']
        
        # Handle multi-class vs single class
        if isinstance(shap_values, list):
            class_shap = shap_values[class_idx][0]  # [class][sample][feature]
        else:
            class_shap = shap_values[0]  # [sample][feature]
            
        return [
            {
                'feature': name,
                'value': float(value),
                'abs_value': abs(float(value)),
                'sign': 'positive' if value > 0 else 'negative'
            }
            for name, value in zip(explanation['shap']['feature_names'], class_shap)
        ]
        
    @classmethod
    def get_top_features(cls, explanation: Dict, top_n: int = 10, class_idx: int = 0) -> List[Dict]:
        """
        Get top N most important features.
        
        Args:
            explanation: Explanation dictionary from explain()
            top_n: Number of top features to return
            class_idx: Index of the class to get features for
            
        Returns:
            List of top N features sorted by absolute SHAP value
        """
        features = cls.get_feature_importance(explanation, class_idx)
        return sorted(features, key=lambda x: x['abs_value'], reverse=True)[:top_n]
