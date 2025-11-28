"""
XGBoost Trainer for Multi-Label Antibiotic Resistance Prediction
Supports GPU acceleration (NVIDIA, AMD, Intel Arc) with automatic detection.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import subprocess
import platform

logger = logging.getLogger(__name__)


class XGBoostTrainer:
    """
    XGBoost trainer for multi-label antibiotic resistance prediction.
    
    Features:
    - Multi-label classification (one model per antibiotic)
    - GPU acceleration with broad hardware support
    - Automatic train/test splitting
    - Model persistence
    """
    
    def __init__(
        self,
        model_name: str = "xgboost_amr_model",
        test_size: float = 0.2,
        random_state: int = 42,
        model_dir: str = "./trained_models"
    ):
        """
        Initialize XGBoost trainer.
        
        Args:
            model_name: Name for the model
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility
            model_dir: Directory to save trained models
        """
        self.model_name = model_name
        self.test_size = test_size
        self.random_state = random_state
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.models: Dict[str, xgb.XGBClassifier] = {}
        self.feature_names: Optional[list] = None
        self.antibiotic_names: Optional[list] = None
        self.device = self._detect_gpu()
    
    def _detect_gpu(self) -> str:
        """
        Detect available GPU and return appropriate device string.
        
        Returns:
            Device string ('cuda', 'cpu', etc.)
        """
        logger.info("Detecting GPU hardware...")
        
        # Try PyTorch CUDA detection
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"NVIDIA GPU detected: {gpu_name}")
                return "cuda"
        except ImportError:
            logger.debug("PyTorch not available for GPU detection")
        
        # Try system-level GPU detection
        try:
            if platform.system() == "Windows":
                # Check for AMD GPU
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                gpu_info = result.stdout.lower()
                
                if "amd" in gpu_info or "radeon" in gpu_info:
                    logger.info("AMD GPU detected")
                    return "cuda"  # XGBoost uses 'cuda' for AMD via ROCm
                elif "intel" in gpu_info and "arc" in gpu_info:
                    logger.info("Intel Arc GPU detected")
                    return "cuda"  # XGBoost may support via oneAPI
            
            elif platform.system() == "Linux":
                # Check for AMD GPU via lspci
                result = subprocess.run(
                    ["lspci"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "amd" in result.stdout.lower() or "radeon" in result.stdout.lower():
                    logger.info("AMD GPU detected")
                    return "cuda"
        
        except Exception as e:
            logger.debug(f"System GPU detection failed: {e}")
        
        logger.info("No compatible GPU detected, using CPU")
        return "cpu"
    
    def train(
        self,
        X: pd.DataFrame,
        Y: pd.DataFrame,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Train XGBoost models for multi-label classification.
        
        Args:
            X: Feature matrix (genomes x k-mers)
            Y: Label matrix (genomes x antibiotics)
            progress_callback: Optional callback for progress updates (0-100)
            
        Returns:
            Dictionary with training metrics
        """
        logger.info("Starting XGBoost training")
        logger.info(f"Data shape: X={X.shape}, Y={Y.shape}")
        logger.info(f"Device: {self.device}")
        
        self.feature_names = list(X.columns)
        self.antibiotic_names = list(Y.columns)
        
        # Split data
        X_train, X_test, Y_train, Y_test = train_test_split(
            X, Y,
            test_size=self.test_size,
            random_state=self.random_state
        )
        
        logger.info(f"Train set: {X_train.shape[0]} samples")
        logger.info(f"Test set: {X_test.shape[0]} samples")
        
        # Train one model per antibiotic
        results = {}
        n_antibiotics = len(self.antibiotic_names)
        
        for idx, antibiotic in enumerate(self.antibiotic_names):
            logger.info(f"Training model for {antibiotic} ({idx+1}/{n_antibiotics})")
            
            # Get labels for this antibiotic
            y_train = Y_train[antibiotic].dropna()
            y_test = Y_test[antibiotic].dropna()
            
            # Filter X to match non-null labels
            X_train_filtered = X_train.loc[y_train.index]
            X_test_filtered = X_test.loc[y_test.index]
            
            if len(y_train) < 5:
                logger.warning(f"Insufficient data for {antibiotic} ({len(y_train)} samples), skipping")
                continue
            
            # Get unique classes in training data
            unique_classes = sorted(y_train.unique())
            n_classes = len(unique_classes)
            
            if n_classes < 2:
                logger.warning(f"Only {n_classes} class(es) for {antibiotic}, skipping")
                continue
            
            # Remap labels to consecutive integers (0, 1, 2, ...)
            # This is required by XGBoost
            label_map = {orig: new for new, orig in enumerate(unique_classes)}
            label_map_reverse = {new: orig for orig, new in label_map.items()}
            
            y_train_mapped = y_train.map(label_map)
            y_test_mapped = y_test.map(label_map)
            
            # Drop test samples with classes not seen in training
            valid_test_mask = y_test_mapped.notna()
            y_test_mapped = y_test_mapped[valid_test_mask]
            X_test_filtered = X_test_filtered.loc[y_test_mapped.index]
            
            if len(y_test_mapped) == 0:
                logger.warning(f"No valid test samples for {antibiotic}, skipping")
                continue
            
            # Configure XGBoost parameters
            params = {
                'objective': 'multi:softmax' if n_classes > 2 else 'binary:logistic',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'random_state': self.random_state,
                'tree_method': 'hist',  # Fast histogram-based method
                'device': self.device
            }
            
            if n_classes > 2:
                params['num_class'] = n_classes
            
            # Train model
            model = xgb.XGBClassifier(**params)
            model.fit(
                X_train_filtered,
                y_train_mapped,
                eval_set=[(X_test_filtered, y_test_mapped)],
                verbose=False
            )
            
            # Store model with label mapping
            self.models[antibiotic] = {
                'model': model,
                'label_map': label_map,
                'label_map_reverse': label_map_reverse
            }
            
            # Evaluate (map predictions back to original labels)
            y_pred_mapped = model.predict(X_test_filtered)
            y_pred = pd.Series(y_pred_mapped).map(label_map_reverse).values
            y_test_original = y_test_mapped.map(label_map_reverse).values
            
            results[antibiotic] = {
                'accuracy': accuracy_score(y_test_original, y_pred),
                'precision': precision_score(y_test_original, y_pred, average='weighted', zero_division=0),
                'recall': recall_score(y_test_original, y_pred, average='weighted', zero_division=0),
                'f1': f1_score(y_test_original, y_pred, average='weighted', zero_division=0),
                'n_train': len(y_train),
                'n_test': len(y_test_mapped),
                'classes': unique_classes
            }
            
            logger.info(
                f"{antibiotic}: Accuracy={results[antibiotic]['accuracy']:.3f}, "
                f"F1={results[antibiotic]['f1']:.3f}"
            )
            
            # Update progress
            if progress_callback:
                progress_callback((idx + 1) / n_antibiotics * 100)
        
        # Calculate overall metrics
        overall_metrics = {
            'avg_accuracy': np.mean([r['accuracy'] for r in results.values()]),
            'avg_precision': np.mean([r['precision'] for r in results.values()]),
            'avg_recall': np.mean([r['recall'] for r in results.values()]),
            'avg_f1': np.mean([r['f1'] for r in results.values()]),
            'per_antibiotic': results,
            'n_models': len(self.models),
            'device': self.device
        }
        
        logger.info("XGBoost training completed")
        logger.info(f"Average F1 Score: {overall_metrics['avg_f1']:.3f}")
        
        return overall_metrics
    
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Predict antibiotic resistance for new samples.
        
        Args:
            X: Feature matrix (genomes x k-mers)
            
        Returns:
            Prediction matrix (genomes x antibiotics)
        """
        if not self.models:
            raise ValueError("No trained models available. Train first.")
        
        predictions = {}
        
        for antibiotic, model in self.models.items():
            predictions[antibiotic] = model.predict(X)
        
        return pd.DataFrame(predictions, index=X.index)
    
    def save_model(self, custom_path: Optional[str] = None) -> Path:
        """
        Save trained models and metadata.
        
        Args:
            custom_path: Optional custom save path
            
        Returns:
            Path to saved model directory
        """
        if custom_path:
            save_dir = Path(custom_path)
        else:
            save_dir = self.model_dir / self.model_name
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save models
        models_file = save_dir / "models.pkl"
        with open(models_file, 'wb') as f:
            pickle.dump(self.models, f)
        
        # Save metadata
        metadata = {
            'model_name': self.model_name,
            'model_type': 'xgboost',
            'feature_names': self.feature_names,
            'antibiotic_names': self.antibiotic_names,
            'n_features': len(self.feature_names) if self.feature_names else 0,
            'n_antibiotics': len(self.antibiotic_names) if self.antibiotic_names else 0,
            'test_size': self.test_size,
            'random_state': self.random_state,
            'device': self.device
        }
        
        metadata_file = save_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {save_dir}")
        return save_dir
    
    def load_model(self, model_path: str) -> None:
        """
        Load trained models and metadata.
        
        Args:
            model_path: Path to model directory
        """
        model_dir = Path(model_path)
        
        # Load models
        models_file = model_dir / "models.pkl"
        with open(models_file, 'rb') as f:
            self.models = pickle.load(f)
        
        # Load metadata
        metadata_file = model_dir / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        self.model_name = metadata['model_name']
        self.feature_names = metadata['feature_names']
        self.antibiotic_names = metadata['antibiotic_names']
        
        logger.info(f"Model loaded from {model_dir}")
        logger.info(f"Antibiotics: {len(self.antibiotic_names)}")
