"""
XGBoost model trainer for antibiotic resistance prediction.
Handles multi-label classification with evaluation metrics.
"""
import xgboost as xgb
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, jaccard_score, classification_report
import pickle
import json
import os
import logging

from config import settings

logger = logging.getLogger(__name__)


class XGBoostTrainer:
    """
    Trains XGBoost models for antibiotic resistance prediction.
    Supports both single multi-output model and separate models per antibiotic.
    """
    
    def __init__(
        self,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42,
        use_gpu: bool = True
    ):
        """
        Initialize XGBoost trainer.
        
        Args:
            max_depth: Maximum tree depth
            learning_rate: Learning rate (eta)
            n_estimators: Number of boosting rounds
            random_state: Random seed for reproducibility
            use_gpu: Whether to use GPU for training (default: True)
        """
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.use_gpu = use_gpu
        self.models: Dict[str, xgb.XGBClassifier] = {}
        self.feature_names: List[str] = []
        self.antibiotic_names: List[str] = []
        
        # Detect GPU availability
        self.device = self._detect_gpu()
        if self.use_gpu and self.device == 'cpu':
            logger.warning("⚠️  GPU requested but not available. Falling back to CPU.")
            logger.warning("   Training will be slower without GPU acceleration.")
        elif self.device == 'cuda':
            logger.info("✅ GPU detected and will be used for training")
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_name = torch.cuda.get_device_name(0)
                    logger.info(f"   GPU: {gpu_name}")
            except:
                pass
    
    def _detect_gpu(self) -> str:
        """Detect if GPU is available for XGBoost (NVIDIA, AMD, Intel, etc.)."""
        if not self.use_gpu:
            return 'cpu'
        
        # Try PyTorch first (supports NVIDIA CUDA, AMD ROCm, Intel, Apple MPS)
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU detected via PyTorch CUDA: {gpu_name}")
                logger.info("Training will use GPU acceleration.")
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                logger.info("Apple Metal GPU detected via PyTorch MPS.")
                logger.info("Note: XGBoost doesn't support MPS yet. Using CPU.")
                return 'cpu'
        except ImportError:
            pass
        
        # Try NVIDIA via nvidia-smi
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                # Extract GPU name from nvidia-smi output
                for line in result.stdout.split('\n'):
                    if 'NVIDIA' in line or 'GeForce' in line or 'Tesla' in line or 'Quadro' in line:
                        logger.info(f"NVIDIA GPU detected: {line.strip()}")
                        logger.info("Training will use GPU acceleration.")
                        return 'cuda'
                logger.info("NVIDIA GPU detected. Training will use GPU acceleration.")
                return 'cuda'
        except:
            pass
        
        # Try AMD ROCm
        try:
            import subprocess
            result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                logger.info("AMD GPU detected via ROCm.")
                logger.info("Training will use GPU acceleration (ROCm/HIP).")
                return 'cuda'  # XGBoost can use ROCm via HIP backend
        except:
            pass
        
        # Try Intel GPU via oneAPI
        try:
            import subprocess
            # Check for Intel GPU via clinfo or sycl-ls
            result = subprocess.run(['clinfo'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and 'Intel' in result.stdout:
                logger.info("Intel GPU detected via OpenCL.")
                logger.info("Note: XGBoost GPU support for Intel is experimental. Trying anyway.")
                return 'cuda'
        except:
            pass
        
        # Check Windows GPU via wmic (works for NVIDIA, AMD, Intel)
        try:
            import subprocess
            import platform
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    output = result.stdout.lower()
                    if any(gpu in output for gpu in ['nvidia', 'geforce', 'quadro', 'tesla']):
                        logger.info("NVIDIA GPU detected via Windows.")
                        logger.info("Training will use GPU acceleration.")
                        return 'cuda'
                    elif any(gpu in output for gpu in ['amd', 'radeon', 'rx']):
                        logger.info("AMD GPU detected via Windows.")
                        logger.info("Training will use GPU acceleration (if ROCm installed).")
                        return 'cuda'
                    elif any(gpu in output for gpu in ['intel', 'arc', 'iris', 'uhd']):
                        # Check if it's discrete (Arc) or integrated
                        if 'arc' in output:
                            logger.info("Intel Arc GPU detected via Windows.")
                            logger.info("Training will use GPU acceleration (experimental).")
                            return 'cuda'
        except:
            pass
        
        logger.warning("No compatible GPU detected. Training will use CPU.")
        logger.info("Supported GPUs: NVIDIA (CUDA), AMD (ROCm), Intel Arc (experimental)")
        return 'cpu'
    
    def train_per_antibiotic(
        self,
        X: np.ndarray,
        y: np.ndarray,
        antibiotic_names: List[str],
        feature_names: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Dict]:
        """
        Train a separate XGBoost model for each antibiotic.
        
        Args:
            X: Feature matrix (n_samples × n_features)
            y: Label matrix (n_samples × n_antibiotics), values in {0, 1, 2, -1}
            antibiotic_names: List of antibiotic names
            feature_names: List of feature (k-mer) names
            progress_callback: Optional callback function(progress_pct, message)
        
        Returns:
            Dictionary with training metrics per antibiotic
        """
        self.feature_names = feature_names
        self.antibiotic_names = antibiotic_names
        
        n_antibiotics = len(antibiotic_names)
        metrics = {}
        
        for i, antibiotic in enumerate(antibiotic_names):
            # Check for cancellation before training each antibiotic
            if progress_callback:
                try:
                    progress_callback(0, f"Preparing to train {antibiotic}...")
                except InterruptedError:
                    logger.warning(f"Training cancelled before {antibiotic}")
                    break
            
            logger.info(f"Training model for {antibiotic} ({i+1}/{n_antibiotics})")
            
            # Get labels for this antibiotic
            y_antibiotic = y[:, i]
            
            # Filter out samples with missing labels (-1)
            valid_mask = y_antibiotic != -1
            X_valid = X[valid_mask]
            y_valid = y_antibiotic[valid_mask]
            
            if len(y_valid) < 10:
                logger.warning(f"Insufficient data for {antibiotic}: {len(y_valid)} samples. Skipping.")
                metrics[antibiotic] = {"error": "insufficient_data", "n_samples": len(y_valid)}
                continue
            
            # Check class distribution
            unique, counts = np.unique(y_valid, return_counts=True)
            logger.info(f"{antibiotic} class distribution: {dict(zip(unique, counts))}")
            
            if len(unique) < 2:
                logger.warning(f"Only one class for {antibiotic}. Skipping.")
                metrics[antibiotic] = {"error": "single_class", "n_samples": len(y_valid)}
                continue
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X_valid, y_valid,
                test_size=0.2,
                random_state=self.random_state,
                stratify=y_valid if len(unique) > 1 else None
            )
            
            # Train model with GPU support
            model_params = {
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate,
                'n_estimators': self.n_estimators,
                'random_state': self.random_state,
                'objective': 'multi:softmax',
                'num_class': 3,  # S, I, R
                'eval_metric': 'mlogloss',
                'tree_method': 'hist',  # Fast histogram-based algorithm
            }
            
            # Add GPU-specific parameters
            if self.device == 'cuda':
                model_params['tree_method'] = 'gpu_hist'
                model_params['predictor'] = 'gpu_predictor'
                model_params['gpu_id'] = 0
                # Note: XGBoost uses CUDA/HIP backend, works with NVIDIA and AMD GPUs
                logger.info("=" * 60)
                logger.info(f"🚀 TRAINING {antibiotic} MODEL ON GPU (CUDA)")
                logger.info(f"   Tree method: gpu_hist")
                logger.info(f"   Predictor: gpu_predictor")
                logger.info(f"   GPU ID: 0")
                try:
                    import torch
                    if torch.cuda.is_available():
                        gpu_name = torch.cuda.get_device_name(0)
                        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        logger.info(f"   GPU: {gpu_name}")
                        logger.info(f"   GPU Memory: {gpu_mem:.2f} GB")
                except:
                    pass
                logger.info("=" * 60)
            else:
                logger.info(f"⚠️  Training {antibiotic} model on CPU (GPU not available or not configured)")
                logger.info(f"   Tree method: hist (CPU-based)")
                logger.info(f"   This will be slower than GPU training")
            
            model = xgb.XGBClassifier(**model_params)
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            # Evaluate
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            antibiotic_metrics = {
                "n_train": len(X_train),
                "n_test": len(X_test),
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "f1_macro": float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
                "f1_weighted": float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
                "jaccard_macro": float(jaccard_score(y_test, y_pred, average='macro', zero_division=0)),
                "jaccard_weighted": float(jaccard_score(y_test, y_pred, average='weighted', zero_division=0)),
            }
            
            # Get per-class metrics
            try:
                report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
                antibiotic_metrics["per_class"] = report
            except:
                pass
            
            # Get feature importances
            importances = model.feature_importances_
            top_indices = np.argsort(importances)[-20:][::-1]  # Top 20 features
            antibiotic_metrics["top_features"] = [
                {
                    "feature": feature_names[idx],
                    "importance": float(importances[idx])
                }
                for idx in top_indices
            ]
            
            metrics[antibiotic] = antibiotic_metrics
            self.models[antibiotic] = model
            
            logger.info(f"{antibiotic} - Accuracy: {antibiotic_metrics['accuracy']:.3f}, "
                       f"F1: {antibiotic_metrics['f1_macro']:.3f}, "
                       f"Jaccard: {antibiotic_metrics['jaccard_macro']:.3f}")
            
            # Update progress
            if progress_callback:
                progress = int((i + 1) / n_antibiotics * 80) + 10  # 10-90% range
                progress_callback(progress, f"Trained model for {antibiotic}")
        
        return metrics
    
    def save_models(self, model_dir: str, model_name: str) -> str:
        """
        Save trained models and metadata.
        
        Args:
            model_dir: Directory to save models
            model_name: Base name for model files
        
        Returns:
            Path to the main model file
        """
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, f"{model_name}.pkl")
        metadata_path = os.path.join(model_dir, f"{model_name}_metadata.json")
        
        # Save all models as a dict
        save_dict = {
            'models': self.models,
            'feature_names': self.feature_names,
            'antibiotic_names': self.antibiotic_names,
            'hyperparameters': {
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate,
                'n_estimators': self.n_estimators
            }
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(save_dict, f)
        
        # Save metadata
        metadata = {
            'model_name': model_name,
            'model_type': 'xgboost',
            'n_antibiotics': len(self.antibiotic_names),
            'n_features': len(self.feature_names),
            'antibiotic_names': self.antibiotic_names,
            'hyperparameters': save_dict['hyperparameters']
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved XGBoost models to {model_path}")
        
        return model_path
    
    @classmethod
    def load_models(cls, model_path: str) -> 'XGBoostTrainer':
        """
        Load trained models from file.
        
        Args:
            model_path: Path to model file
        
        Returns:
            XGBoostTrainer instance with loaded models
        """
        with open(model_path, 'rb') as f:
            save_dict = pickle.load(f)
        
        trainer = cls()
        trainer.models = save_dict['models']
        trainer.feature_names = save_dict['feature_names']
        trainer.antibiotic_names = save_dict['antibiotic_names']
        trainer.max_depth = save_dict['hyperparameters']['max_depth']
        trainer.learning_rate = save_dict['hyperparameters']['learning_rate']
        trainer.n_estimators = save_dict['hyperparameters']['n_estimators']
        
        logger.info(f"Loaded XGBoost models from {model_path}")
        
        return trainer
    
    def predict(self, X: np.ndarray) -> Dict[str, int]:
        """
        Make predictions for all antibiotics.
        
        Args:
            X: Feature vector or matrix
        
        Returns:
            Dictionary mapping antibiotic to prediction (0=S, 1=I, 2=R)
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        predictions = {}
        for antibiotic, model in self.models.items():
            pred = model.predict(X)[0]
            predictions[antibiotic] = int(pred)
        
        return predictions
    
    def predict_proba(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Get prediction probabilities for all antibiotics.
        
        Args:
            X: Feature vector or matrix
        
        Returns:
            Dictionary mapping antibiotic to probability array [P(S), P(I), P(R)]
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)
        
        probabilities = {}
        for antibiotic, model in self.models.items():
            proba = model.predict_proba(X)[0]
            probabilities[antibiotic] = proba
        
        return probabilities

