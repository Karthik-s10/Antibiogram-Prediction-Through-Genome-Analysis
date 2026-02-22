"""
XGBoost SHAP explainer for multi-antibiotic models.
Handles dictionary model structure from your training job f0849bdd.
"""
import xgboost as xgb  # type: ignore
import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from typing import Dict, List, Tuple, Optional, Any, Union
import pickle
import json
import logging
from pathlib import Path

from .shap_utils import SHAPUtils, SHAPExplanation  # type: ignore

logger = logging.getLogger(__name__)

class XGBoostExplainer:
    """
    Enhanced XGBoost explainer for multi-antibiotic models.
    Handles the dictionary model structure from job f0849bdd.
    """
    
    def __init__(
        self,
        models_dir: str = "trained_models",
        model_file: str = "xgboost_f0849bdd.pkl",
        features_file: str = "xgboost_f0849bdd_features.json",
        metadata_file: str = "xgboost_f0849bdd_metadata.json"
    ):
        """
        Initialize XGBoost explainer.
        
        Args:
            models_dir: Directory containing XGBoost models
            model_file: Main model pickle file
            features_file: Feature names JSON file
            metadata_file: Model metadata JSON file
        """
        self.models_dir = Path(models_dir)
        self.model_file = self.models_dir / model_file
        self.features_file = self.models_dir / features_file
        self.metadata_file = self.models_dir / metadata_file
        self.shap_utils = SHAPUtils()
        self.models = {}
        self.feature_names = {}
        self.explainers = {}
        
    def load_models(self) -> Dict[str, Any]:
        """Load all XGBoost models from dictionary structure."""
        if not self.model_file.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_file}")
        
        with open(self.model_file, 'rb') as f:
            model_dict = pickle.load(f)
        
        logger.info(f"Loaded {len(model_dict.get('models', {}))} XGBoost models")
        return model_dict
    
    def load_feature_names(self) -> List[str]:
        """Load feature names from JSON file."""
        if not self.features_file.exists():
            logger.warning(f"Features file not found: {self.features_file}")
            # Generate generic feature names
            metadata = self.load_metadata()
            n_features = metadata.get('n_features', 1000)
            return [f"kmer_{i}" for i in range(n_features)]
        
        with open(self.features_file, 'r') as f:
            features_data = json.load(f)
            feature_names = features_data.get('feature_names', [])
            logger.info(f"Loaded {len(feature_names)} feature names")
            return feature_names
    
    def load_metadata(self) -> Dict[str, Any]:
        """Load model metadata."""
        if not self.metadata_file.exists():
            logger.warning(f"Metadata file not found: {self.metadata_file}")
            return {}
        
        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)
            logger.info(f"Loaded metadata: {metadata}")
            return metadata
    
    def load_model(self, antibiotic: str) -> Optional[xgb.XGBClassifier]:
        """Load specific antibiotic model."""
        models = self.load_models()
        model_dict = models.get('models', {})
        
        if antibiotic not in model_dict:
            logger.warning(f"Antibiotic {antibiotic} not found in models")
            return None
        
        model = model_dict[antibiotic]
        
        # Ensure it's an XGBoost model
        if not isinstance(model, xgb.XGBClassifier):
            logger.warning(f"Model for {antibiotic} is not XGBClassifier: {type(model)}")
            return None
        
        logger.info(f"Loaded model for {antibiotic}: {type(model)}")
        return model
    
    def get_explainer(self, antibiotic: str) -> Optional[Any]:
        """Get or create SHAP explainer for specific antibiotic."""
        if antibiotic in self.explainers:
            return self.explainers[antibiotic]
        
        model = self.load_model(antibiotic)
        if model is None:
            return None
        
        try:
            import shap  # type: ignore
            explainer = shap.TreeExplainer(model, model_output="probability")
            self.explainers[antibiotic] = explainer
            logger.info(f"Created SHAP explainer for {antibiotic}")
            return explainer
        except Exception as e:
            logger.error(f"Error creating explainer for {antibiotic}: {str(e)}")
            return None
    
    def get_feature_names(self, antibiotic: str) -> List[str]:
        """Get feature names for specific antibiotic."""
        if antibiotic in self.feature_names:
            return self.feature_names[antibiotic]
        
        # Load feature names
        feature_names = self.load_feature_names()
        
        # If specific antibiotic has its own features, use those
        metadata = self.load_metadata()
        antibiotic_names = metadata.get('antibiotic_names', [])
        
        if antibiotic in antibiotic_names:
            # Find index of antibiotic
            antibiotic_idx = antibiotic_names.index(antibiotic)
            feature_names_data = self.load_feature_names()
            if 'feature_names' in feature_names_data:  # type: ignore
                antibiotic_features = feature_names_data['feature_names']  # type: ignore
                if antibiotic_idx < len(antibiotic_features):
                    return antibiotic_features[antibiotic_idx]
        
        # Return generic feature names as fallback
        n_features = metadata.get('n_features', 1000)
        return [f"kmer_{i}" for i in range(n_features)]
    
    def explain_single_sample(
        self,
        antibiotic: str,
        features: Union[np.ndarray, pd.DataFrame],
        prediction: Optional[str] = None,
        probability: Optional[float] = None
    ) -> SHAPExplanation:
        """
        Generate SHAP explanation for a single sample.
        """
        model = self.load_model(antibiotic)
        if model is None:
            raise ValueError(f"Model not available for antibiotic: {antibiotic}")
        
        explainer = self.get_explainer(antibiotic)
        if explainer is None:
            raise ValueError(f"Explainer not available for antibiotic: {antibiotic}")
        
        feature_names = self.get_feature_names(antibiotic)
        
        # Convert to numpy array if DataFrame
        if isinstance(features, pd.DataFrame):
            feature_array = features.values
        else:
            feature_array = np.array(features)
        
        try:
            # Generate SHAP values
            shap_values = explainer.shap_values(feature_array.reshape(1, -1))
            
            # Get base value
            base_value = explainer.expected_value
            
            # Get prediction if not provided
            if prediction is None:
                prediction_proba = model.predict_proba(feature_array.reshape(1, -1))[0]
                prediction_class = np.argmax(prediction_proba)
                classes = ['S', 'I', 'R']
                prediction = classes[prediction_class]
                probability = float(prediction_proba[prediction_class])
            else:
                probability = probability or 0.0
            
            return SHAPExplanation(
                shap_values=shap_values,
                feature_names=feature_names,
                base_values=base_value,
                data=feature_array,
                prediction=prediction,
                probability=probability,
                model_type="XGBoost",
                antibiotic=antibiotic,
                explanation_type="feature_importance",
                metadata={
                    'job_id': 'f0849bdd',
                    'model_path': str(self.model_file),
                    'feature_count': len(feature_names),
                    'available_antibiotics': len(self.load_models().get('models', {}))
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation for {antibiotic}: {str(e)}")
            raise
    
    def explain_batch(
        self,
        antibiotic: str,
        features_batch: Union[List[np.ndarray], pd.DataFrame],
        predictions: Optional[List[str]] = None,
        probabilities: Optional[List[float]] = None
    ) -> List[SHAPExplanation]:
        """
        Generate SHAP explanations for a batch of samples.
        """
        model = self.load_model(antibiotic)
        if model is None:
            raise ValueError(f"Model not available for antibiotic: {antibiotic}")
        
        explainer = self.get_explainer(antibiotic)
        if explainer is None:
            raise ValueError(f"Explainer not available for antibiotic: {antibiotic}")
        
        feature_names = self.get_feature_names(antibiotic)
        
        # Convert to numpy array if DataFrame
        if isinstance(features_batch, list) and len(features_batch) > 0:
            if isinstance(features_batch[0], pd.DataFrame):
                feature_array = np.array([df.values for df in features_batch])
            else:
                feature_array = np.array(features_batch)
        else:
            feature_array = np.array(features_batch)
        
        explanations = []
        
        try:
            # Generate SHAP values for batch
            shap_values = explainer.shap_values(feature_array)
            
            # Get predictions if not provided
            if predictions is None:
                prediction_probas = model.predict_proba(feature_array)
                classes = ['S', 'I', 'R']
                predictions = [classes[np.argmax(proba)] for proba in prediction_probas]
                probabilities = [float(np.max(proba)) for proba in prediction_probas]
            else:
                probabilities = probabilities or [0.0] * len(feature_array)
            
            # Create explanation for each sample
            for i in range(len(feature_array)):
                if len(shap_values.shape) > 2:
                    sample_shap = shap_values[i]
                else:
                    sample_shap = shap_values[i:i+1]
                
                explanations.append(SHAPExplanation(
                    shap_values=sample_shap,
                    feature_names=feature_names,
                    base_values=explainer.expected_value,
                    data=feature_array[i],
                    prediction=predictions[i] if predictions else None,
                    probability=probabilities[i] if probabilities else None,
                    model_type="XGBoost",
                    antibiotic=antibiotic,
                    explanation_type="feature_importance",
                    metadata={
                        'job_id': 'f0849bdd',
                        'model_path': str(self.model_file),
                        'feature_count': len(feature_names),
                        'sample_index': i,
                        'batch_size': len(feature_array)
                    }
                ))
            
            return explanations
            
        except Exception as e:
            logger.error(f"Error generating batch SHAP explanations for {antibiotic}: {str(e)}")
            raise
    
    def get_global_feature_importance(
        self,
        antibiotic: str,
        background_samples: Optional[np.ndarray] = None,
        n_samples: int = 100
    ) -> Dict[str, float]:
        """
        Get global feature importance for an antibiotic model.
        """
        model = self.load_model(antibiotic)
        if model is None:
            raise ValueError(f"Model not available for antibiotic: {antibiotic}")
        
        explainer = self.get_explainer(antibiotic)
        if explainer is None:
            raise ValueError(f"Explainer not available for antibiotic: {antibiotic}")
        
        feature_names = self.get_feature_names(antibiotic)
        
        try:
            # Generate SHAP values for background
            if background_samples is None:
                # Generate synthetic background data
                n_features = len(feature_names)
                background_samples = np.random.normal(0, 1, (n_samples, n_features))
            
            shap_values = explainer.shap_values(background_samples)
            
            # Calculate mean absolute SHAP values for each feature
            if len(shap_values.shape) > 1:
                mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
            else:
                mean_abs_shap = np.abs(shap_values)
            
            # Create importance dictionary
            importance_dict = dict(zip(feature_names, mean_abs_shap))
            
            # Sort by importance
            sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            return sorted_importance
            
        except Exception as e:
            logger.error(f"Error getting global feature importance for {antibiotic}: {str(e)}")
            raise
    
    def get_available_antibiotics(self) -> List[str]:
        """Get list of available antibiotics."""
        models = self.load_models()
        model_dict = models.get('models', {})
        return list(model_dict.keys())
    
    def clear_cache(self):
        """Clear cached explainers and feature names."""
        self.explainers.clear()
        self.feature_names.clear()
        self.models.clear()
        logger.info("Cleared XGBoost explainer cache")
