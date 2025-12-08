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
import time

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
        # Per-antibiotic mapping from encoded XGBoost class index -> original S/I/R code (0,1,2)
        self.label_inv_mappings: Dict[str, Dict[int, int]] = {}
        
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
        
        overall_start = time.time()
        per_antibiotic_durations = []
        
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
            
            if len(y_valid) < 5:
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
            
            # Encode labels to a contiguous range per antibiotic so XGBoost is happy
            # For example, if original labels are {0,2}, we map them to {0,1} but
            # remember how to map predictions back to {0,2}.
            unique_sorted = np.sort(unique)
            label_to_enc = {orig: idx for idx, orig in enumerate(unique_sorted)}
            enc_to_label = {idx: orig for orig, idx in label_to_enc.items()}
            y_valid_enc = np.array([label_to_enc[v] for v in y_valid], dtype=int)
            
            # Train/test split (on encoded labels). If the least populated class
            # has fewer than 2 samples, sklearn's stratified split will fail,
            # so we fall back to a non-stratified split in that edge case. We
            # also guard against cases where the test set would end up with
            # fewer samples than classes, which causes scikit-learn to raise
            # "The test_size = 1 should be greater or equal to the number of
            # classes = 2". In that situation we skip this antibiotic instead
            # of failing the entire training job.
            unique_enc, counts_enc = np.unique(y_valid_enc, return_counts=True)
            min_count = counts_enc.min()
            use_stratify = len(unique_enc) > 1 and min_count >= 2

            if use_stratify:
                n_classes = len(unique_enc)
                # train_test_split will compute the test set size as
                # ceil(test_size * n_samples); mimic that here to detect
                # problematic tiny test sets ahead of time.
                estimated_n_test = int(np.ceil(0.2 * len(y_valid_enc)))
                if estimated_n_test < n_classes:
                    logger.warning(
                        f"Skipping {antibiotic} for XGBoost training: "
                        f"only {len(y_valid_enc)} samples available with "
                        f"{n_classes} classes; a 20% test split would produce "
                        f"only {estimated_n_test} test samples, which is fewer "
                        f"than the number of classes."
                    )
                    metrics[antibiotic] = {
                        "error": "insufficient_test_samples_for_stratified_split",
                        "n_samples": int(len(y_valid)),
                        "classes": [int(c) for c in unique],
                        "estimated_n_test": int(estimated_n_test),
                    }
                    continue

            if not use_stratify:
                logger.warning(
                    f"Not using stratified split for {antibiotic} because "
                    f"the least populated class has only {min_count} samples."
                )

            X_train, X_test, y_train, y_test = train_test_split(
                X_valid, y_valid_enc,
                test_size=0.2,
                random_state=self.random_state,
                stratify=y_valid_enc if use_stratify else None
            )
            
            # Train model with GPU support using multi-class softmax on the
            # per-antibiotic encoded labels. num_class is simply the number of
            # unique encoded classes for this antibiotic (2 or 3).
            num_classes = len(unique_sorted)
            model_params = {
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate,
                'n_estimators': self.n_estimators,
                'random_state': self.random_state,
                'objective': 'multi:softmax',
                'num_class': num_classes,
                'eval_metric': 'mlogloss',
                'tree_method': 'hist',  # Fast histogram-based algorithm
            }

            # Add device-specific parameters following XGBoost 2.x recommendations
            if self.device == 'cuda':
                # Use histogram tree method with device='cuda' instead of deprecated gpu_hist
                model_params['device'] = 'cuda'
                logger.info("=" * 60)
                logger.info(f"🚀 TRAINING {antibiotic} MODEL ON GPU (CUDA)")
                logger.info(f"   Tree method: hist")
                logger.info(f"   Device: cuda")
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
                model_params['device'] = 'cpu'
                logger.info(f"⚠️  Training {antibiotic} model on CPU (GPU not available or not configured)")
                logger.info(f"   Tree method: hist (CPU-based)")
                logger.info(f"   Device: cpu")
                logger.info(f"   This will be slower than GPU training")
            
            model = xgb.XGBClassifier(**model_params)

            ab_start = time.time()

            try:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_test, y_test)],
                    verbose=False
                )
            except ValueError as e:
                # XGBoost 2.x can raise a ValueError if it believes the label
                # classes are invalid (e.g. expecting [0, 1] but seeing [0, 2]).
                # We already encode labels to a contiguous range per antibiotic,
                # but in case of any mismatch we skip this antibiotic instead of
                # failing the entire training job.
                logger.error(
                    f"{antibiotic} - XGBoost fit failed with ValueError: {e}"
                )
                logger.error(
                    f"{antibiotic} - raw classes: {unique}, encoded classes: {unique_enc}"
                )
                metrics[antibiotic] = {
                    "error": "fit_error_invalid_classes",
                    "n_samples": int(len(y_valid)),
                    "classes": [int(c) for c in unique],
                    "message": str(e),
                }
                # Skip to next antibiotic without aborting the whole job
                continue

            ab_elapsed = time.time() - ab_start
            per_antibiotic_durations.append(ab_elapsed)

            # Evaluate
            y_pred_enc = model.predict(X_test)
            # Map encoded predictions and test labels back to original S/I/R codes
            y_test_orig = np.array([enc_to_label[int(v)] for v in y_test])
            y_pred = np.array([enc_to_label[int(v)] for v in y_pred_enc])
            
            # Calculate metrics
            antibiotic_metrics = {
                "n_train": len(X_train),
                "n_test": len(X_test),
                "accuracy": float(accuracy_score(y_test_orig, y_pred)),
                "f1_macro": float(f1_score(y_test_orig, y_pred, average='macro', zero_division=0)),
                "f1_weighted": float(f1_score(y_test_orig, y_pred, average='weighted', zero_division=0)),
                "jaccard_macro": float(jaccard_score(y_test_orig, y_pred, average='macro', zero_division=0)),
                "jaccard_weighted": float(jaccard_score(y_test_orig, y_pred, average='weighted', zero_division=0)),
            }
            
            # Get per-class metrics
            try:
                report = classification_report(y_test_orig, y_pred, output_dict=True, zero_division=0)
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
            # Remember label mapping for this antibiotic (encoded -> original S/I/R code)
            self.label_inv_mappings[antibiotic] = enc_to_label
            
            logger.info(
                f"{antibiotic} - Accuracy: {antibiotic_metrics['accuracy']:.3f}, "
                f"F1: {antibiotic_metrics['f1_macro']:.3f}, "
                f"Jaccard: {antibiotic_metrics['jaccard_macro']:.3f}"
            )

            done = i + 1
            remaining = n_antibiotics - done
            avg_time = sum(per_antibiotic_durations) / max(len(per_antibiotic_durations), 1)
            eta_sec = remaining * avg_time
            total_elapsed = time.time() - overall_start

            logger.info(
                f"[{done}/{n_antibiotics}] {antibiotic} trained in {ab_elapsed/60:.1f} min; "
                f"remaining {remaining}, ETA {eta_sec/60:.1f} min "
                f"(elapsed {total_elapsed/60:.1f} min)"
            )

            # Update progress
            if progress_callback:
                progress = int((i + 1) / n_antibiotics * 80) + 10  # 10-90% range
                msg = (
                    f"{antibiotic} trained in {ab_elapsed/60:.1f} min; "
                    f"{done}/{n_antibiotics} antibiotics trained; "
                    f"ETA {eta_sec/60:.1f} min"
                )
                progress_callback(progress, msg)
        
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

        # If a subdirectory for this model already exists (e.g. imported demos),
        # save into that folder using model.pkl + metadata.json. Otherwise, keep
        # the existing flat file layout.
        model_subdir = os.path.join(model_dir, model_name)
        if os.path.isdir(model_subdir):
            target_dir = model_subdir
            model_path = os.path.join(target_dir, "model.pkl")
            metadata_path = os.path.join(target_dir, "metadata.json")
        else:
            target_dir = model_dir
            model_path = os.path.join(target_dir, f"{model_name}.pkl")
            metadata_path = os.path.join(target_dir, f"{model_name}_metadata.json")

        os.makedirs(target_dir, exist_ok=True)

        # Save all models as a dict (overwrite existing binary if present)
        save_dict = {
            'models': self.models,
            'feature_names': self.feature_names,
            'antibiotic_names': self.antibiotic_names,
            'label_inv_mappings': self.label_inv_mappings,
            'hyperparameters': {
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate,
                'n_estimators': self.n_estimators
            }
        }

        with open(model_path, 'wb') as f:
            pickle.dump(save_dict, f)

        # Build new metadata
        metadata = {
            'model_name': model_name,
            'model_type': 'xgboost',
            'n_antibiotics': len(self.antibiotic_names),
            'n_features': len(self.feature_names),
            'antibiotic_names': self.antibiotic_names,
            'hyperparameters': save_dict['hyperparameters']
        }

        # If an existing metadata.json is present (e.g. imported demo), merge it
        # by appending/updating keys instead of discarding the old structure.
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    existing = json.load(f)
                if isinstance(existing, dict):
                    merged = existing.copy()
                    merged.update(metadata)
                    metadata = merged
            except Exception as e:
                logger.warning(f"Failed to merge existing XGBoost metadata at {metadata_path}: {e}")

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
        trainer.label_inv_mappings = save_dict.get('label_inv_mappings', {})
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
            pred_enc = model.predict(X)[0]
            # Map encoded prediction back to original label if mapping exists
            enc_to_label = self.label_inv_mappings.get(antibiotic)
            if enc_to_label is not None:
                pred = enc_to_label.get(int(pred_enc), int(pred_enc))
            else:
                pred = int(pred_enc)
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
            proba_raw = model.predict_proba(X)[0]
            enc_to_label = self.label_inv_mappings.get(antibiotic)
            if enc_to_label is not None:
                # Expand encoded probabilities into a 3-element [P(S), P(I), P(R)] vector
                proba3 = np.zeros(3, dtype=float)
                n_classes = proba_raw.shape[0]
                for enc_idx, orig_label in enc_to_label.items():
                    if 0 <= enc_idx < n_classes and 0 <= orig_label < 3:
                        proba3[orig_label] = proba_raw[enc_idx]
                proba = proba3
            else:
                # Assume proba_raw already aligns with [0,1,2]
                proba = proba_raw
            probabilities[antibiotic] = proba
        
        return probabilities

