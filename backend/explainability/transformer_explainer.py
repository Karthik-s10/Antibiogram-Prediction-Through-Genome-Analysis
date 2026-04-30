"""
DNABERT Transformer SHAP explainer for antibiotic resistance prediction.

This implementation uses **attention rollup** (averaging attention heads across
all transformer layers) to produce token-level importance scores.  It is
pure-PyTorch and does **not** require TensorFlow or a running `shap`
background explainer, removing the source of the previous TF import conflict.

Model layout expected on disk (matches DNABERTTrainer per_antibiotic_dir_v1):
  trained_models/transformer_<job_id>/
      metadata.json
      model.pkl                          # DNABERTTrainer pickle
      tokenizer/                         # Shared HuggingFace tokenizer
      antibiotics/
          <idx>_<antibiotic_name>/
              model.safetensors          # Per-antibiotic fine-tuned weights
              config.json
              ...
"""
from __future__ import annotations

import glob
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np  # type: ignore
import torch  # type: ignore
from transformers import (  # type: ignore
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BertConfig,
)

from .shap_utils import SHAPUtils, SHAPExplanation  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: attention rollup
# ---------------------------------------------------------------------------

def _attention_rollup(attentions: Tuple[torch.Tensor, ...]) -> np.ndarray:
    """
    Average all heads across all layers, then multiply (attention rollup).

    attentions: tuple of (batch, heads, seq, seq) tensors – one per layer.
    Returns a 1-D np.ndarray of length seq_len containing per-token importance.
    """
    # Stack and average across heads → (n_layers, seq, seq)
    avg = torch.stack([a.squeeze(0).mean(dim=0) for a in attentions], dim=0)  # (L, S, S)

    # Rollup: multiply layer matrices  (can be approximated by summing rows)
    # We use the simpler "sum over all layers" approximation:
    rollup = avg.sum(dim=0)  # (S, S)

    # Importance per token = column sum (how much each token is attended to)
    importance = rollup.sum(dim=0)  # (S,)
    importance = importance.cpu().numpy().astype(float)

    # Normalise to [0, 1]
    total = importance.sum()
    if total > 0:
        importance = importance / total
    return importance


# ---------------------------------------------------------------------------
# Main explainer
# ---------------------------------------------------------------------------

class TransformerExplainer:
    """
    Token-level importance explainer for DNABERT models.

    Uses attention-rollup (pure PyTorch, no TensorFlow) to derive per-token
    importance scores from the real fine-tuned checkpoints saved by
    DNABERTTrainer.
    """

    def __init__(self, models_dir: str = "trained_models"):
        self.models_dir = Path(models_dir)
        self.shap_utils = SHAPUtils()

        # Caches keyed by antibiotic name
        self._tokenizer_cache: Dict[str, Any] = {}
        self._model_cache: Dict[str, Any] = {}

        # Pre-scan once so we know what models are available
        self._job_dir: Optional[Path] = self._find_job_dir()
        if self._job_dir:
            logger.info(f"TransformerExplainer: using model at {self._job_dir}")
        else:
            logger.warning(
                "TransformerExplainer: no transformer_* directory found under %s. "
                "DNABERT explanations will return empty importance.",
                self.models_dir,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_job_dir(self) -> Optional[Path]:
        """Return the first transformer_* directory found."""
        candidates = sorted(self.models_dir.glob("transformer_*"))
        return candidates[0] if candidates else None

    def _antibiotic_to_dir_name(self, antibiotic: str) -> Optional[Path]:
        """Map antibiotic string → antibiotics/<idx>_<name> subdirectory."""
        if self._job_dir is None:
            return None
        ab_dir = self._job_dir / "antibiotics"
        if not ab_dir.is_dir():
            return None

        # Normalise: lower, replace spaces/slashes/parens with underscore
        norm = re.sub(r"[\s/\\()\-]+", "_", antibiotic.strip().lower())

        # Try exact suffix match first
        for d in ab_dir.iterdir():
            suffix = re.sub(r"^\d+_", "", d.name)  # strip leading index
            if suffix == norm or suffix.replace("_", " ") == antibiotic.lower():
                return d

        # Fallback: substring
        for d in ab_dir.iterdir():
            if norm in d.name:
                return d

        return None

    def _load_shared_tokenizer(self) -> Optional[Any]:
        if "shared" in self._tokenizer_cache:
            return self._tokenizer_cache["shared"]
        if self._job_dir is None:
            return None
        tok_path = self._job_dir / "tokenizer"
        if not tok_path.is_dir():
            return None
        try:
            tok = AutoTokenizer.from_pretrained(str(tok_path))
            self._tokenizer_cache["shared"] = tok
            logger.info("Loaded shared tokenizer from %s", tok_path)
            return tok
        except Exception as exc:
            logger.warning("Could not load shared tokenizer: %s", exc)
            return None

    def _load_model_for_antibiotic(self, antibiotic: str) -> Optional[Any]:
        if antibiotic in self._model_cache:
            return self._model_cache[antibiotic]

        ab_dir = self._antibiotic_to_dir_name(antibiotic)
        if ab_dir is None:
            logger.warning("No checkpoint directory found for antibiotic '%s'", antibiotic)
            return None

        # Check safetensors or pytorch_model.bin exists
        ckpt_files = list(ab_dir.glob("model.safetensors")) + list(ab_dir.glob("pytorch_model.bin"))
        if not ckpt_files:
            logger.warning("No model checkpoint in %s", ab_dir)
            return None

        try:
            model = AutoModelForSequenceClassification.from_pretrained(
                str(ab_dir),
                output_attentions=True,
                ignore_mismatched_sizes=True,
            )
            model.eval()
            self._model_cache[antibiotic] = model
            logger.info("Loaded DNABERT checkpoint for '%s' from %s", antibiotic, ab_dir)
            return model
        except Exception as exc:
            logger.warning("Could not load model for antibiotic '%s': %s", antibiotic, exc)
            return None

    def _tokenize(self, sequence: str, tokenizer) -> Dict[str, torch.Tensor]:
        """Tokenize a raw DNA sequence, clean + format for DNABERT."""
        clean = re.sub(r"[^ATCG]", "", sequence.upper())
        # DNABERT 6-mer tokenizer: split into 6-mer space-separated string
        # If the tokenizer already handles raw sequences, this is a no-op.
        try:
            test = tokenizer.encode("ATCGAT", add_special_tokens=False)
        except Exception:
            test = []

        # Check if tokenizer is the 6-mer type (vocab has entries like "ATCGAT")
        # If so, build the 6-mer sentence manually
        if "ATCGAT" in tokenizer.get_vocab():
            k = 6
            kmers = [clean[i : i + k] for i in range(len(clean) - k + 1)]
            sentence = " ".join(kmers) if kmers else clean
        else:
            sentence = clean

        enc = tokenizer(
            sentence,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        return enc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def explain_single_sample(
        self,
        antibiotic: str,
        sequence: str,
        prediction: Optional[str] = None,
        probability: Optional[float] = None,
    ) -> SHAPExplanation:
        """
        Return a SHAPExplanation using attention-rollup token importance.

        Works with the real per-antibiotic DNABERT checkpoints.
        Falls back to uniform importance if the checkpoint is not found.
        """
        tokenizer = self._load_shared_tokenizer()
        model = self._load_model_for_antibiotic(antibiotic)

        # --- tokenise ---
        if tokenizer is not None:
            inputs = self._tokenize(sequence, tokenizer)
            tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        else:
            # Synthetic tokens — just k-mers
            clean = re.sub(r"[^ATCG]", "", sequence.upper())
            tokens = [clean[i : i + 6] for i in range(0, min(len(clean), 512), 6)] or ["[UNK]"]
            inputs = None

        # --- forward pass & attention ---
        pred_label = prediction or "Unknown"
        pred_prob = probability or 0.0
        if model is not None and inputs is not None:
            try:
                with torch.no_grad():
                    outputs = model(**inputs)

                # Get prediction from logits
                logits = outputs.logits
                probs_tensor = torch.softmax(logits, dim=-1)
                pred_idx = int(torch.argmax(probs_tensor, dim=-1)[0])
                class_map = {0: "S", 1: "I", 2: "R"}
                pred_label = prediction or class_map.get(pred_idx, "Unknown")
                pred_prob = probability if probability is not None else float(probs_tensor[0, pred_idx])

                # Attention rollup for token importance
                if hasattr(outputs, "attentions") and outputs.attentions:
                    importance = _attention_rollup(outputs.attentions)
                else:
                    importance = np.ones(len(tokens)) / len(tokens)
            except Exception as exc:
                logger.warning("Forward pass failed for '%s': %s", antibiotic, exc)
                importance = np.ones(len(tokens)) / len(tokens)
        else:
            importance = np.ones(len(tokens)) / len(tokens)

        # Trim / pad importance to token count
        if len(importance) > len(tokens):
            importance = importance[: len(tokens)]
        elif len(importance) < len(tokens):
            importance = np.pad(importance, (0, len(tokens) - len(importance)))

        # Shape as (1, n_tokens) to mimic shap_values structure
        shap_values = importance.reshape(1, -1)
        feature_names = [f"token_{i}_{t}" for i, t in enumerate(tokens)]

        return SHAPExplanation(
            shap_values=shap_values,
            feature_names=feature_names,
            base_values=0.0,
            data=sequence,
            prediction=pred_label,
            probability=pred_prob,
            model_type="DNABERT",
            antibiotic=antibiotic,
            explanation_type="attention_rollup",
            metadata={
                "model_path": str(self._antibiotic_to_dir_name(antibiotic) or "not_found"),
                "sequence_length": len(sequence),
                "token_count": len(tokens),
                "tokens": tokens,
                "explanation_method": "attention_rollup",
            },
        )

    def explain_batch(
        self,
        antibiotic: str,
        sequences: List[str],
        predictions: Optional[List[str]] = None,
        probabilities: Optional[List[float]] = None,
    ) -> List[SHAPExplanation]:
        """Explain a batch of sequences. Calls explain_single_sample per item."""
        results = []
        for i, seq in enumerate(sequences):
            pred = predictions[i] if predictions and i < len(predictions) else None
            prob = probabilities[i] if probabilities and i < len(probabilities) else None
            results.append(self.explain_single_sample(antibiotic, seq, pred, prob))
        return results

    def get_token_importance_summary(
        self, antibiotic: str, sequences: List[str], top_k: int = 50
    ) -> Dict[str, Any]:
        """Aggregate token importance across a list of sequences."""
        explanations = self.explain_batch(antibiotic, sequences)
        token_importance: Dict[str, List[float]] = {}

        for exp in explanations:
            vals = exp.shap_values
            if vals.ndim > 1:
                vals = vals[0]
            for fname, v in zip(exp.feature_names, vals):
                token = fname.split("_", 2)[-1]
                token_importance.setdefault(token, []).append(float(v))

        token_stats: Dict[str, Any] = {}
        for token, values in token_importance.items():
            arr = np.array(values)
            token_stats[token] = {
                "mean_importance": float(np.mean(arr)),
                "std_importance": float(np.std(arr)),
                "max_importance": float(np.max(arr)),
                "min_importance": float(np.min(arr)),
                "frequency": len(arr),
                "abs_mean_importance": float(np.abs(arr).mean()),
            }

        sorted_tokens = dict(
            sorted(token_stats.items(), key=lambda x: x[1]["abs_mean_importance"], reverse=True)
        )
        return {
            "token_importance": sorted_tokens,
            "total_sequences": len(sequences),
            "unique_tokens": len(token_stats),
            "top_tokens": dict(list(sorted_tokens.items())[:top_k]),
        }

    def create_explanation_summary(self, antibiotics: List[str]) -> Dict[str, Any]:
        """Summarise token importance across multiple antibiotics."""
        summary: Dict[str, Any] = {
            "antibiotics": {},
            "common_tokens": {},
            "model_types": ["DNABERT"],
            "total_models": len(antibiotics),
        }
        all_importance: Dict[str, List[float]] = {}
        sample_seqs = [
            "ATCGATCGATCGATCGATCG",
            "GCTAGCTAGCTAGCTAGCTA",
            "CCCCGGGGAAAATTTT",
        ]
        for ab in antibiotics:
            try:
                tok_summary = self.get_token_importance_summary(ab, sample_seqs)
                summary["antibiotics"][ab] = tok_summary
                for token, stats in tok_summary["token_importance"].items():
                    all_importance.setdefault(token, []).append(stats["mean_importance"])
            except Exception as exc:
                logger.warning("Could not process antibiotic '%s': %s", ab, exc)
                summary["antibiotics"][ab] = {"error": str(exc)}

        for token, importances in all_importance.items():
            if len(importances) > 1:
                arr = np.array(importances)
                summary["common_tokens"][token] = {
                    "mean_importance": float(np.mean(arr)),
                    "std_importance": float(np.std(arr)),
                    "max_importance": float(np.max(arr)),
                    "min_importance": float(np.min(arr)),
                    "frequency": len(arr),
                }

        summary["common_tokens"] = dict(
            sorted(
                summary["common_tokens"].items(),
                key=lambda x: x[1]["mean_importance"],
                reverse=True,
            )
        )
        return summary
