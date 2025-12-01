"""
DNABERT Transformer trainer for antibiotic resistance prediction.
Uses Hugging Face transformers library with fine-tuning.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, jaccard_score
import pickle
import json
import os
import logging
import time

# Import torch with error handling for DLL loading issues
try:
    import torch
    TORCH_AVAILABLE = True
    # Try to access CUDA to see if DLLs load correctly
    # DLL loading errors can happen at import or when accessing CUDA
    try:
        _ = torch.cuda.is_available()
        TORCH_CUDA_LOADED = True
    except (OSError, RuntimeError, AttributeError, Exception) as e:
        # CUDA DLLs failed to load, but PyTorch is installed - use CPU
        error_type = type(e).__name__
        error_msg = str(e)
        logging.warning(f"PyTorch CUDA DLLs failed to load ({error_type}: {error_msg}). Falling back to CPU mode.")
        logging.warning("Training will work but will be slower on CPU. To fix GPU support:")
        logging.warning("  1. Install Visual C++ Redistributables: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        logging.warning("  2. Or reinstall PyTorch CPU-only: pip install torch torchvision torchaudio --force-reinstall")
        TORCH_CUDA_LOADED = False
except (ImportError, OSError, RuntimeError, Exception) as e:
    # Handle both missing package and DLL loading errors
    error_type = type(e).__name__
    error_msg = str(e)
    
    if isinstance(e, ImportError):
        TORCH_AVAILABLE = False
        TORCH_CUDA_LOADED = False
        logging.error("PyTorch not installed! Install it with: pip install torch")
        logging.error("For GPU support, install CUDA version: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
    elif "DLL" in error_msg or "dll" in error_msg.lower() or error_type == "OSError":
        # DLL error during import - try to continue with CPU mode
        TORCH_AVAILABLE = False  # Can't use torch if import fails
        TORCH_CUDA_LOADED = False
        logging.error(f"PyTorch DLL loading error during import ({error_type}: {error_msg})")
        logging.error("PyTorch cannot be imported. Please reinstall:")
        logging.error("  pip uninstall torch torchvision torchaudio")
        logging.error("  pip install torch torchvision torchaudio")
    else:
        TORCH_AVAILABLE = False
        TORCH_CUDA_LOADED = False
        logging.error(f"Error importing PyTorch ({error_type}): {error_msg}")

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
        EarlyStoppingCallback,
        TrainerCallback,
    )
    from transformers.models.bert.configuration_bert import BertConfig
    from datasets import Dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    TRANSFORMERS_AVAILABLE = False
    if not TORCH_AVAILABLE:
        logging.error("Transformers library requires PyTorch. Install PyTorch first!")
    else:
        logging.error(f"Transformers library not available: {e}")
        logging.error("Install with: pip install transformers datasets")

from config import settings

logger = logging.getLogger(__name__)


class DNABERTEpochLoggingCallback(TrainerCallback):
    """Custom callback to log clear epoch/step progress for DNABERT training."""

    def __init__(self, antibiotic: str, total_epochs: int):
        self.antibiotic = antibiotic
        self.total_epochs = total_epochs
        self.epoch_start_time: Optional[float] = None
        self.max_steps: int = 0
        self.steps_per_epoch: float = 0.0

    def on_train_begin(self, args, state, control, **kwargs):
        self.max_steps = max(int(getattr(state, "max_steps", 0) or 0), 0)
        if self.total_epochs > 0 and self.max_steps > 0:
            self.steps_per_epoch = self.max_steps / float(self.total_epochs)
        else:
            self.steps_per_epoch = 0.0
        if self.max_steps > 0 and self.steps_per_epoch > 0:
            logger.info(
                f"{self.antibiotic} - DNABERT training started: "
                f"{self.total_epochs} epochs, ~{self.steps_per_epoch:.0f} steps/epoch, "
                f"{self.max_steps} total steps"
            )
        else:
            logger.info(
                f"{self.antibiotic} - DNABERT training started for {self.total_epochs} epochs "
                f"(steps per epoch will be determined dynamically)"
            )

    def on_epoch_begin(self, args, state, control, **kwargs):
        current_epoch = int(state.epoch) + 1 if state.epoch is not None else 1
        self.epoch_start_time = time.time()
        if self.steps_per_epoch > 0:
            logger.info(
                f"{self.antibiotic} - Starting epoch {current_epoch}/{self.total_epochs} "
                f"(~{self.steps_per_epoch:.0f} steps this epoch)"
            )
        else:
            logger.info(
                f"{self.antibiotic} - Starting epoch {current_epoch}/{self.total_epochs}"
            )

    def on_epoch_end(self, args, state, control, **kwargs):
        elapsed = (time.time() - self.epoch_start_time) if self.epoch_start_time is not None else 0.0
        current_epoch = int(state.epoch) if state.epoch is not None else 0
        global_step = int(getattr(state, "global_step", 0) or 0)
        max_steps = self.max_steps or int(getattr(state, "max_steps", 0) or 0)
        if max_steps > 0:
            progress_pct = 100.0 * float(global_step) / float(max_steps)
        else:
            progress_pct = 0.0
        max_steps_str = str(max_steps) if max_steps > 0 else "?"
        logger.info(
            f"{self.antibiotic} - Completed epoch {current_epoch}/{self.total_epochs} "
            f"in {elapsed/60:.1f} min "
            f"(global step {global_step}/{max_steps_str}, "
            f"overall {progress_pct:.1f}% of planned training steps)"
        )


class DNABERTTrainer:
    """
    Trains DNABERT models for antibiotic resistance prediction.
    Uses gene-level classification with genome-level aggregation.
    """
    
    def __init__(
        self,
        model_name: str = "zhihan1996/DNA_bert_6",
        max_length: int = 512,
        batch_size: int = 16,
        epochs: int = 3,
        learning_rate: float = 2e-5,
        random_state: int = 42,
        kmer_size: int = 10,
    ):
        """
        Initialize DNABERT trainer.
        
        Args:
            model_name: Pre-trained DNABERT model from Hugging Face
            max_length: Maximum sequence length
            batch_size: Training batch size
            epochs: Number of training epochs
            learning_rate: Learning rate for fine-tuning
            random_state: Random seed
        """
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch not installed!\n"
                "Install PyTorch with: pip install torch\n"
                "For GPU support (CUDA), use:\n"
                "  CUDA 12.1: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121\n"
                "  CUDA 11.8: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n"
                "  CPU only: pip install torch torchvision torchaudio"
            )
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers library not installed.\n"
                "Install with: pip install transformers datasets\n"
                "Note: PyTorch must be installed first!"
            )
        
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.kmer_size = kmer_size
        
        self.tokenizer = None
        self.models: Dict[str, any] = {}
        self.antibiotic_names: List[str] = []
        
        # Detect device - prioritize GPU
        self.device = self._detect_gpu_device()
        if self.device.type == 'cuda':
            logger.info("=" * 60)
            logger.info("✅ DNABERT Transformer: GPU detected and will be used")
            try:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                logger.info(f"   GPU: {gpu_name}")
                logger.info(f"   GPU Memory: {gpu_mem:.2f} GB")
                logger.info(f"   CUDA Version: {torch.version.cuda}")
            except:
                pass
            logger.info("=" * 60)
        else:
            logger.warning("⚠️  DNABERT Transformer: GPU not available, using CPU")
            logger.warning("   Training will be significantly slower on CPU")
    
    def _detect_gpu_device(self) -> torch.device:
        """
        Detect GPU device, prioritizing CUDA.
        Supports NVIDIA (CUDA), AMD (ROCm), and Intel Arc.
        Falls back to CPU if CUDA DLLs fail to load.
        """
        if not TORCH_AVAILABLE:
            return torch.device('cpu')
        
        # If CUDA DLLs failed to load, use CPU
        if not TORCH_CUDA_LOADED:
            logger.warning("CUDA DLLs not available, using CPU mode for PyTorch")
            return torch.device('cpu')
        
        # Try CUDA first (NVIDIA, AMD ROCm, Intel Arc with CUDA support)
        try:
            if torch.cuda.is_available():
                return torch.device('cuda')
        except (OSError, RuntimeError) as e:
            logger.warning(f"CUDA check failed ({e}), falling back to CPU")
            return torch.device('cpu')
        
        # Try other GPU backends (ROCm, etc.)
        # For now, if CUDA is not available, use CPU
        # ROCm can work through CUDA compatibility layers
        return torch.device('cpu')
    
    def train_per_antibiotic(
        self,
        gene_df: pd.DataFrame,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Dict]:
        """
        Train a separate DNABERT model for each antibiotic.
        
        Args:
            gene_df: DataFrame with columns: gene_sequence, antibiotic, label
            progress_callback: Optional callback(progress_pct, message)
        
        Returns:
            Dictionary with training metrics per antibiotic
        """
        # Load tokenizer (DNABERT-6 expects case-sensitive k-mers, so disable lowercasing)
        logger.info(f"Loading tokenizer from {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, do_lower_case=False)
        
        # Get unique antibiotics
        antibiotics = sorted(gene_df['antibiotic'].unique())
        self.antibiotic_names = antibiotics
        
        n_antibiotics = len(antibiotics)
        metrics = {}
        
        overall_start = time.time()
        per_antibiotic_durations = []
        
        for i, antibiotic in enumerate(antibiotics):
            # Check for cancellation before training each antibiotic
            if progress_callback:
                try:
                    progress_callback(0, f"Preparing to train DNABERT for {antibiotic}...")
                except InterruptedError:
                    logger.warning(f"Training cancelled before {antibiotic}")
                    break
            
            logger.info(f"Training DNABERT model for {antibiotic} ({i+1}/{n_antibiotics})")
            
            # Log GPU usage for this antibiotic
            if self.device.type == 'cuda':
                logger.info("=" * 60)
                logger.info(f"🚀 TRAINING DNABERT {antibiotic} MODEL ON GPU (CUDA)")
                logger.info(f"   Device: {self.device}")
                try:
                    gpu_name = torch.cuda.get_device_name(0)
                    logger.info(f"   GPU: {gpu_name}")
                except:
                    pass
                logger.info("=" * 60)
            else:
                logger.warning(f"⚠️  Training {antibiotic} on CPU (GPU not available)")
            
            # Filter data for this antibiotic
            antibiotic_df = gene_df[gene_df['antibiotic'] == antibiotic].copy()
            
            # Require a modest minimum number of genes so training is at least somewhat stable
            if len(antibiotic_df) < 20:
                logger.warning(f"Insufficient data for {antibiotic}: {len(antibiotic_df)} genes. Skipping.")
                metrics[antibiotic] = {"error": "insufficient_data", "n_samples": len(antibiotic_df)}
                continue
            
            # Check class distribution
            label_counts = antibiotic_df['label'].value_counts()
            logger.info(f"{antibiotic} label distribution: {label_counts.to_dict()}")
            
            if len(label_counts) < 2:
                logger.warning(f"Only one class for {antibiotic}. Skipping.")
                metrics[antibiotic] = {"error": "single_class"}
                continue
            
            try:
                ab_start = time.time()
                # Train model for this antibiotic
                model, antibiotic_metrics = self._train_single_model(
                    antibiotic_df,
                    antibiotic,
                    progress_callback,
                    i,
                    n_antibiotics
                )
                ab_elapsed = time.time() - ab_start
                per_antibiotic_durations.append(ab_elapsed)
                
                self.models[antibiotic] = model
                metrics[antibiotic] = antibiotic_metrics
                
                logger.info(
                    f"{antibiotic} - Accuracy: {antibiotic_metrics.get('accuracy', 0):.3f}, "
                    f"F1: {antibiotic_metrics.get('f1_macro', 0):.3f}"
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

                if progress_callback:
                    try:
                        progress = int(((i + 1) / n_antibiotics) * 80) + 10
                        msg = (
                            f"{antibiotic} trained in {ab_elapsed/60:.1f} min; "
                            f"{done}/{n_antibiotics} antibiotics trained; "
                            f"ETA {eta_sec/60:.1f} min"
                        )
                        progress_callback(progress, msg)
                    except InterruptedError:
                        logger.warning(f"Training cancelled after {antibiotic}")
                        break
                
            except Exception as e:
                ab_elapsed = time.time() - ab_start
                err_str = str(e)
                lower_err = err_str.lower()
                if "out of memory" in lower_err:
                    logger.error(
                        f"CUDA out of memory while training {antibiotic} after {ab_elapsed/60:.1f} min: {err_str}"
                    )
                    if TORCH_AVAILABLE and self.device.type == 'cuda':
                        try:
                            torch.cuda.empty_cache()
                        except Exception:
                            pass
                    metrics[antibiotic] = {
                        "error": "cuda_oom",
                        "message": err_str,
                    }
                else:
                    logger.error(
                        f"Error training {antibiotic} after {ab_elapsed/60:.1f} min: {err_str}",
                        exc_info=True,
                    )
                    metrics[antibiotic] = {"error": err_str}
        
        return metrics
    
    def _train_single_model(
        self,
        data_df: pd.DataFrame,
        antibiotic: str,
        progress_callback: Optional[callable],
        antibiotic_idx: int,
        total_antibiotics: int
    ) -> Tuple[any, Dict]:
        """Train a single DNABERT model for one antibiotic."""
        
        # Split data
        train_df, test_df = train_test_split(
            data_df,
            test_size=0.2,
            random_state=self.random_state,
            stratify=data_df['label']
        )
        
        # Tokenize sequences
        logger.info(f"Tokenizing {len(train_df)} training genes...")
        train_encodings = self._tokenize_sequences(train_df['gene_sequence'].tolist())
        test_encodings = self._tokenize_sequences(test_df['gene_sequence'].tolist())
        
        # Create datasets
        train_dataset = self._create_dataset(train_encodings, train_df['label'].tolist())
        test_dataset = self._create_dataset(test_encodings, test_df['label'].tolist())
        
        # Load pre-trained model
        logger.info(f"Loading pre-trained model: {self.model_name}")
        model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=3,  # S, I, R
        )
        # Move model to GPU immediately after loading
        model.to(self.device)
        logger.info(f"Model moved to device: {self.device}")
        
        # Training arguments
        output_dir = f"{settings.model_storage_path}/dnabert_{antibiotic}_temp"
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine if we can use mixed precision (fp16) - requires CUDA GPU
        use_fp16 = self.device.type == 'cuda' and torch.cuda.is_available()
        if use_fp16:
            logger.info("   Using mixed precision (FP16) for faster training")
        
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=self.epochs,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            learning_rate=self.learning_rate,
            weight_decay=0.01,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            logging_strategy="epoch",
            logging_steps=10,
            save_total_limit=2,
            fp16=use_fp16,  # Use mixed precision if GPU available
            dataloader_num_workers=0,  # Windows compatibility
            # Explicitly set device
            no_cuda=(self.device.type != 'cuda'),  # Disable CUDA only if not using GPU
            use_cpu=(self.device.type == 'cpu'),  # Use CPU only if GPU not available
            disable_tqdm=True,
        )
        
        if self.device.type == 'cuda':
            logger.info(f"   Training arguments configured for GPU")
            logger.info(f"   Batch size per device: {self.batch_size}")
            logger.info(f"   Mixed precision (FP16): {use_fp16}")
        
        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            callbacks=[
                EarlyStoppingCallback(early_stopping_patience=2),
                DNABERTEpochLoggingCallback(antibiotic=antibiotic, total_epochs=self.epochs),
            ],
        )
        
        # Train
        logger.info(f"Training {antibiotic} model for {self.epochs} epochs on {self.device}...")
        try:
            trainer.train()
        except Exception as e:
            err_str = str(e)
            lower_err = err_str.lower()
            if "out of memory" in lower_err:
                logger.error(f"CUDA/Runtime out-of-memory while training {antibiotic}: {err_str}")
                if self.device.type == 'cuda' and torch.cuda.is_available():
                    try:
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
            # Check if it's a cancellation error
            if "InterruptedError" in str(type(e)) or "cancelled" in lower_err:
                raise InterruptedError("Training job was cancelled by user")
            raise
        
        # Evaluate
        logger.info("Evaluating model...")
        predictions = trainer.predict(test_dataset)
        pred_labels = np.argmax(predictions.predictions, axis=1)
        true_labels = test_df['label'].values
        
        # Calculate metrics
        accuracy = accuracy_score(true_labels, pred_labels)
        f1_macro = f1_score(true_labels, pred_labels, average='macro', zero_division=0)
        f1_weighted = f1_score(true_labels, pred_labels, average='weighted', zero_division=0)
        jaccard_macro = jaccard_score(true_labels, pred_labels, average='macro', zero_division=0)
        jaccard_weighted = jaccard_score(true_labels, pred_labels, average='weighted', zero_division=0)
        
        metrics = {
            "n_train": len(train_df),
            "n_test": len(test_df),
            "accuracy": float(accuracy),
            "f1_macro": float(f1_macro),
            "f1_weighted": float(f1_weighted),
            "jaccard_macro": float(jaccard_macro),
            "jaccard_weighted": float(jaccard_weighted)
        }
        
        # Update progress
        if progress_callback:
            progress = int(((antibiotic_idx + 1) / total_antibiotics) * 80) + 10
            progress_callback(progress, f"Trained DNABERT for {antibiotic}")
        
        return model, metrics
    
    def _tokenize_sequences(self, sequences: List[str]) -> Dict:
        """Tokenize DNA sequences for DNABERT."""
        # Convert sequences to k-mer format
        kmer_sequences = []
        
        for seq in sequences:
            # Create k-mer representation using configured kmer_size
            kmers = []
            k = self.kmer_size
            if len(seq) >= k:
                for i in range(len(seq) - k + 1):
                    kmer = seq[i:i+k]
                    if all(base in 'ACGT' for base in kmer):
                        kmers.append(kmer)

            # Limit number of tokens to max_length
            kmer_seq = ' '.join(kmers[: self.max_length])
            kmer_sequences.append(kmer_seq)
        
        # Tokenize
        encodings = self.tokenizer(
            kmer_sequences,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return encodings
    
    def _create_dataset(self, encodings: Dict, labels: List[int]) -> Dataset:
        """Create HuggingFace Dataset from encodings and labels."""
        dataset_dict = {
            'input_ids': encodings['input_ids'],
            'attention_mask': encodings['attention_mask'],
            'labels': torch.tensor(labels)
        }
        
        return Dataset.from_dict({
            'input_ids': encodings['input_ids'].tolist(),
            'attention_mask': encodings['attention_mask'].tolist(),
            'labels': labels
        })
    
    def predict_genome(self, gene_sequences: List[str]) -> Dict[str, int]:
        """
        Predict resistance for a genome using gene-level predictions.
        Aggregates gene predictions to genome level.
        
        Args:
            gene_sequences: List of gene sequences from the genome
        
        Returns:
            Dictionary mapping antibiotic to prediction (0=S, 1=I, 2=R)
        """
        predictions, _ = self.predict_genome_with_proba(gene_sequences)
        return predictions

    def predict_genome_with_proba(
        self,
        gene_sequences: List[str]
    ) -> Tuple[Dict[str, int], Dict[str, np.ndarray]]:
        """Predict genome-level resistance and per-class probabilities.

        Uses a single tokenization step and one DNABERT forward pass per
        antibiotic model to compute both the aggregated genome prediction
        and class probabilities (S/I/R) for each antibiotic.
        """
        if not self.tokenizer:
            raise ValueError("Models not loaded. Train or load models first.")

        import torch.nn.functional as F

        # Tokenize all gene sequences once and reuse across antibiotics
        encodings = self._tokenize_sequences(gene_sequences)
        input_ids = encodings['input_ids'].to(self.device)
        attention_mask = encodings['attention_mask'].to(self.device)

        genome_predictions: Dict[str, int] = {}
        predictions_proba: Dict[str, np.ndarray] = {}

        # Level-A gene markers: store per-gene class predictions for each antibiotic
        # so that downstream code can surface which genes were called R/I.
        self.gene_level_predictions: Dict[str, List[int]] = {}

        # Per-gene class probabilities (S/I/R) for each antibiotic, used to
        # derive per-gene impact scores downstream.
        self.gene_level_probabilities: Dict[str, np.ndarray] = {}

        for antibiotic, model in self.models.items():
            # Predict for each gene for this antibiotic model
            model.eval()
            with torch.no_grad():
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                probs = F.softmax(logits, dim=-1)

                # Gene-level predictions
                gene_predictions = torch.argmax(logits, dim=1).cpu().numpy()

            # Persist raw gene-level predictions (0=S,1=I,2=R) for explainability
            try:
                self.gene_level_predictions[antibiotic] = [int(v) for v in gene_predictions.tolist()]
            except Exception:
                # Best-effort only; do not break predictions if conversion fails
                pass

            # Persist per-gene probabilities for each antibiotic
            try:
                self.gene_level_probabilities[antibiotic] = probs.cpu().numpy()
            except Exception:
                # Best-effort only
                pass

            # Aggregate: if any gene is resistant (2), genome is resistant
            # Otherwise, if any gene is intermediate (1), genome is intermediate
            # Otherwise, genome is susceptible (0)
            if np.any(gene_predictions == 2):
                genome_pred = 2  # Resistant
            elif np.any(gene_predictions == 1):
                genome_pred = 1  # Intermediate
            else:
                genome_pred = 0  # Susceptible

            genome_predictions[antibiotic] = int(genome_pred)

            # Per-class probabilities (S/I/R) averaged across genes
            avg_probs = probs.mean(dim=0).cpu().numpy()
            predictions_proba[antibiotic] = avg_probs

        return genome_predictions, predictions_proba
    
    def save_models(self, model_dir: str, model_name: str) -> str:
        """Save trained models and tokenizer."""
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

        # Save models and tokenizer (overwrite existing binary if present)
        save_dict = {
            'models': self.models,
            'tokenizer': self.tokenizer,
            'antibiotic_names': self.antibiotic_names,
            'hyperparameters': {
                'model_name': self.model_name,
                'max_length': self.max_length,
                'batch_size': self.batch_size,
                'epochs': self.epochs,
                'learning_rate': self.learning_rate,
                'kmer_size': self.kmer_size,
            },
        }

        with open(model_path, 'wb') as f:
            pickle.dump(save_dict, f)

        # Build new metadata
        metadata = {
            'model_name': model_name,
            'model_type': 'transformer_dnabert',
            'base_model': self.model_name,
            'n_antibiotics': len(self.antibiotic_names),
            'antibiotic_names': self.antibiotic_names
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
                logger.warning(f"Failed to merge existing Transformer metadata at {metadata_path}: {e}")

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved DNABERT models to {model_path}")

        return model_path
    
    @classmethod
    def load_models(cls, model_path: str) -> 'DNABERTTrainer':
        """Load trained models from file."""
        with open(model_path, 'rb') as f:
            save_dict = pickle.load(f)
        
        trainer = cls()
        trainer.models = save_dict['models']
        trainer.tokenizer = save_dict['tokenizer']
        trainer.antibiotic_names = save_dict['antibiotic_names']
        trainer.model_name = save_dict['hyperparameters']['model_name']
        trainer.max_length = save_dict['hyperparameters']['max_length']
        trainer.kmer_size = save_dict['hyperparameters'].get('kmer_size', trainer.kmer_size)
        
        logger.info(f"Loaded DNABERT models from {model_path}")
        
        return trainer

