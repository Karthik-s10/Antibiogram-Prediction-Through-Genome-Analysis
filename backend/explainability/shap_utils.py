"""
SHAP utilities for model explainability.
Common functions and data structures for SHAP explanations.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import shap
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class SHAPExplanation:
    """Data structure for SHAP explanation results."""
    shap_values: Union[np.ndarray, List[np.ndarray]]
    feature_names: List[str]
    base_values: Union[float, np.ndarray]
    data: Union[np.ndarray, List[np.ndarray]]
    prediction: Union[str, int, float]
    probability: Optional[float] = None
    model_type: str = "unknown"
    antibiotic: str = "unknown"
    explanation_type: str = "feature_importance"
    metadata: Optional[Dict[str, Any]] = None

class SHAPUtils:
    """Utility class for SHAP explanations and visualizations."""
    
    def __init__(self):
        self.explanation_cache = {}
        
    def prepare_feature_names(self, feature_data: Dict[str, Any]) -> List[str]:
        """Prepare feature names from k-mer data or other feature sources."""
        if isinstance(feature_data, dict) and 'kmer_features' in feature_data:
            return list(feature_data['kmer_features'].keys())
        elif isinstance(feature_data, pd.DataFrame):
            return feature_data.columns.tolist()
        else:
            return [f"feature_{i}" for i in range(len(feature_data))]
    
    def rank_features_by_importance(self, shap_values: np.ndarray, 
                                  feature_names: List[str],
                                  top_k: int = 20) -> List[Tuple[str, float]]:
        """Rank features by absolute SHAP value importance."""
        if len(shap_values.shape) > 1:
            # For multi-class, use mean absolute value across classes
            mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
        else:
            mean_abs_shap = np.abs(shap_values)
            
        feature_importance = list(zip(feature_names, mean_abs_shap))
        feature_importance.sort(key=lambda x: x[1], reverse=True)
        
        return feature_importance[:top_k]
    
    def create_force_plot_data(self, explanation: SHAPExplanation) -> Dict[str, Any]:
        """Create data structure for force plot visualization."""
        if len(explanation.shap_values.shape) > 1:
            # Multi-class case
            shap_vals = explanation.shap_values[0]  # Use first class
        else:
            shap_vals = explanation.shap_values
            
        feature_importance = self.rank_features_by_importance(
            shap_vals, explanation.feature_names
        )
        
        return {
            'base_value': float(explanation.base_values) if np.isscalar(explanation.base_values) else explanation.base_values.tolist(),
            'shap_values': shap_vals.tolist(),
            'feature_names': explanation.feature_names,
            'feature_importance': feature_importance,
            'prediction': explanation.prediction,
            'probability': explanation.probability,
            'model_type': explanation.model_type,
            'antibiotic': explanation.antibiotic
        }
    
    def create_summary_plot_data(self, explanations: List[SHAPExplanation]) -> Dict[str, Any]:
        """Create data structure for summary plot visualization."""
        all_shap_values = []
        all_feature_names = []
        
        for exp in explanations:
            if len(exp.shap_values.shape) > 1:
                shap_vals = exp.shap_values[0]
            else:
                shap_vals = exp.shap_values
                
            all_shap_values.extend(shap_vals)
            all_feature_names.extend(exp.feature_names)
        
        # Create feature importance summary
        feature_importance = {}
        for name, value in zip(all_feature_names, all_shap_values):
            if name not in feature_importance:
                feature_importance[name] = []
            feature_importance[name].append(value)
        
        # Calculate mean importance for each feature
        summary_importance = []
        for name, values in feature_importance.items():
            mean_val = np.mean(values)
            std_val = np.std(values)
            summary_importance.append({
                'feature': name,
                'mean_importance': mean_val,
                'std_importance': std_val,
                'abs_mean_importance': abs(mean_val)
            })
        
        # Sort by absolute importance
        summary_importance.sort(key=lambda x: x['abs_mean_importance'], reverse=True)
        
        return {
            'feature_importance': summary_importance[:50],  # Top 50 features
            'total_features': len(feature_importance),
            'total_explanations': len(explanations)
        }
    
    def create_waterfall_plot_data(self, explanation: SHAPExplanation) -> Dict[str, Any]:
        """Create data structure for waterfall plot visualization."""
        if len(explanation.shap_values.shape) > 1:
            shap_vals = explanation.shap_values[0]
        else:
            shap_vals = explanation.shap_values
            
        # Get base value
        base_value = float(explanation.base_values) if np.isscalar(explanation.base_values) else explanation.base_values[0]
        
        # Calculate cumulative sum for waterfall plot
        cumulative_values = []
        current_sum = base_value
        
        feature_data = []
        for i, (name, shap_val) in enumerate(zip(explanation.feature_names, shap_vals)):
            current_sum += shap_val
            cumulative_values.append(current_sum)
            
            feature_data.append({
                'feature': name,
                'shap_value': shap_val,
                'cumulative_value': current_sum,
                'contribution_type': 'positive' if shap_val > 0 else 'negative'
            })
        
        # Sort by absolute contribution
        feature_data.sort(key=lambda x: abs(x['shap_value']), reverse=True)
        
        return {
            'base_value': base_value,
            'final_prediction': current_sum,
            'features': feature_data,
            'prediction': explanation.prediction,
            'model_type': explanation.model_type,
            'antibiotic': explanation.antibiotic
        }
    
    def cache_explanation(self, key: str, explanation: SHAPExplanation):
        """Cache explanation for faster retrieval."""
        self.explanation_cache[key] = explanation
        
    def get_cached_explanation(self, key: str) -> Optional[SHAPExplanation]:
        """Get cached explanation if available."""
        return self.explanation_cache.get(key)
    
    def clear_cache(self):
        """Clear explanation cache."""
        self.explanation_cache.clear()
    
    def format_explanation_for_frontend(self, explanation: SHAPExplanation) -> Dict[str, Any]:
        """Format explanation data for frontend consumption."""
        return {
            'shap_values': explanation.shap_values.tolist() if hasattr(explanation.shap_values, 'tolist') else explanation.shap_values,
            'feature_names': explanation.feature_names,
            'base_values': explanation.base_values.tolist() if hasattr(explanation.base_values, 'tolist') else explanation.base_values,
            'prediction': explanation.prediction,
            'probability': explanation.probability,
            'model_type': explanation.model_type,
            'antibiotic': explanation.antibiotic,
            'explanation_type': explanation.explanation_type,
            'metadata': explanation.metadata or {},
            'force_plot_data': self.create_force_plot_data(explanation),
            'waterfall_plot_data': self.create_waterfall_plot_data(explanation)
        }
