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
        EarlyStoppingCallback
    )
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


class DNABERTTrainer:
    """
    Trains DNABERT models for antibiotic resistance prediction.
    Uses gene-level classification with genome-level aggregation.
    """
    
    def __init__(
        self,
        model_name: str = "zhihan1996/DNABERT-6",
        max_length: int = 512,
        batch_size: int = 16,
        epochs: int = 3,
        learning_rate: float = 2e-5,
        random_state: int = 42
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
        # Load tokenizer
        logger.info(f"Loading tokenizer from {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        
        # Get unique antibiotics
        antibiotics = sorted(gene_df['antibiotic'].unique())
        self.antibiotic_names = antibiotics
        
        n_antibiotics = len(antibiotics)
        metrics = {}
        
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
            
            if len(antibiotic_df) < 50:
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
                # Train model for this antibiotic
                model, antibiotic_metrics = self._train_single_model(
                    antibiotic_df,
                    antibiotic,
                    progress_callback,
                    i,
                    n_antibiotics
                )
                
                self.models[antibiotic] = model
                metrics[antibiotic] = antibiotic_metrics
                
                logger.info(f"{antibiotic} - Accuracy: {antibiotic_metrics.get('accuracy', 0):.3f}, "
                           f"F1: {antibiotic_metrics.get('f1_macro', 0):.3f}")
                
            except Exception as e:
                logger.error(f"Error training {antibiotic}: {e}", exc_info=True)
                metrics[antibiotic] = {"error": str(e)}
        
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
            trust_remote_code=True
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
            logging_steps=10,
            save_total_limit=2,
            fp16=use_fp16,  # Use mixed precision if GPU available
            dataloader_num_workers=0,  # Windows compatibility
            # Explicitly set device
            no_cuda=(self.device.type != 'cuda'),  # Disable CUDA only if not using GPU
            use_cpu=(self.device.type == 'cpu')  # Use CPU only if GPU not available
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
            callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
        )
        
        # Train
        logger.info(f"Training {antibiotic} model for {self.epochs} epochs on {self.device}...")
        try:
            trainer.train()
        except Exception as e:
            # Check if it's a cancellation error
            if "InterruptedError" in str(type(e)) or "cancelled" in str(e).lower():
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
            # Create 6-mer representation
            kmers = []
            for i in range(len(seq) - 5):
                kmer = seq[i:i+6]
                if all(base in 'ACGT' for base in kmer):
                    kmers.append(kmer)
            
            kmer_seq = ' '.join(kmers[:self.max_length])  # Limit length
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
        if not self.tokenizer:
            raise ValueError("Models not loaded. Train or load models first.")
        
        genome_predictions = {}
        
        for antibiotic, model in self.models.items():
            # Tokenize genes
            encodings = self._tokenize_sequences(gene_sequences)
            
            # Move to device
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
            
            # Predict for each gene
            model.eval()
            with torch.no_grad():
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                gene_predictions = torch.argmax(outputs.logits, dim=1).cpu().numpy()
            
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
        
        return genome_predictions
    
    def save_models(self, model_dir: str, model_name: str) -> str:
        """Save trained models and tokenizer."""
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, f"{model_name}.pkl")
        
        # Save models and tokenizer
        save_dict = {
            'models': self.models,
            'tokenizer': self.tokenizer,
            'antibiotic_names': self.antibiotic_names,
            'hyperparameters': {
                'model_name': self.model_name,
                'max_length': self.max_length,
                'batch_size': self.batch_size,
                'epochs': self.epochs,
                'learning_rate': self.learning_rate
            }
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(save_dict, f)
        
        # Save metadata
        metadata = {
            'model_name': model_name,
            'model_type': 'transformer_dnabert',
            'base_model': self.model_name,
            'n_antibiotics': len(self.antibiotic_names),
            'antibiotic_names': self.antibiotic_names
        }
        
        metadata_path = os.path.join(model_dir, f"{model_name}_metadata.json")
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
        
        logger.info(f"Loaded DNABERT models from {model_path}")
        
        return trainer

