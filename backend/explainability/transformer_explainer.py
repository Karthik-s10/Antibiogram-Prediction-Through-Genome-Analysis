"""
DNABERT Transformer SHAP explainer for antibiotic resistance prediction.
Provides token-level and sequence-level explanations using GradientExplainer.
"""
import numpy as np
import pandas as pd
import torch
import shap
import pickle
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import re

from .shap_utils import SHAPUtils, SHAPExplanation

logger = logging.getLogger(__name__)

class TransformerExplainer:
    """SHAP explainer for DNABERT transformer models."""
    
    def __init__(self, models_dir: str = "trained_models/transformer"):
        """
        Initialize Transformer explainer.
        
        Args:
            models_dir: Directory containing trained DNABERT models
        """
        self.models_dir = Path(models_dir)
        self.shap_utils = SHAPUtils()
        self.explainers = {}  # Cache explainers for each model
        self.tokenizers = {}  # Cache tokenizers for each model
        self.models = {}  # Cache models for each model
        
    def load_model_and_tokenizer(self, antibiotic: str):
        """Load DNABERT model and tokenizer for specific antibiotic."""
        if antibiotic in self.models:
            return self.models[antibiotic], self.tokenizers[antibiotic]
            
        model_path = self.models_dir / f"transformer_{antibiotic}"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        try:
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForSequenceClassification.from_pretrained(model_path)
            
            # Set model to evaluation mode
            model.eval()
            
            # Move to GPU if available
            if torch.cuda.is_available():
                model = model.cuda()
            
            self.tokenizers[antibiotic] = tokenizer
            self.models[antibiotic] = model
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Error loading model for {antibiotic}: {str(e)}")
            raise
    
    def get_explainer(self, antibiotic: str, model=None, tokenizer=None):
        """Get or create SHAP GradientExplainer for model."""
        if antibiotic in self.explainers:
            return self.explainers[antibiotic]
            
        if model is None or tokenizer is None:
            model, tokenizer = self.load_model_and_tokenizer(antibiotic)
        
        # Create background data (can be a set of representative sequences)
        # For now, use a simple background - in practice, use real background sequences
        background_sequences = [
            "ATCGATCGATCGATCG",  # Placeholder sequences
            "GCTAGCTAGCTAGCTA",
            "TTTTAAAACCCGGGGG"
        ]
        
        # Tokenize background sequences
        background_inputs = tokenizer(
            background_sequences,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            for key in background_inputs:
                background_inputs[key] = background_inputs[key].cuda()
        
        # Create GradientExplainer
        explainer = shap.GradientExplainer(
            model,
            background_inputs,
            local_smoothing=0.01  # Add small smoothing for stability
        )
        
        self.explainers[antibiotic] = explainer
        return explainer
    
    def preprocess_sequence(self, sequence: str, tokenizer) -> Dict[str, torch.Tensor]:
        """Preprocess DNA sequence for transformer input."""
        # Clean sequence (remove non-DNA characters)
        clean_sequence = re.sub(r'[^ATCG]', '', sequence.upper())
        
        # Tokenize sequence
        inputs = tokenizer(
            clean_sequence,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
            return_attention_mask=True
        )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            for key in inputs:
                inputs[key] = inputs[key].cuda()
        
        return inputs
    
    def explain_single_sample(self,
                            antibiotic: str,
                            sequence: str,
                            prediction: Optional[str] = None,
                            probability: Optional[float] = None) -> SHAPExplanation:
        """
        Generate SHAP explanation for a single DNA sequence.
        
        Args:
            antibiotic: Antibiotic name
            sequence: DNA sequence
            prediction: Model prediction (S/I/R)
            probability: Prediction probability
            
        Returns:
            SHAPExplanation object
        """
        try:
            # Load model and tokenizer
            model, tokenizer = self.load_model_and_tokenizer(antibiotic)
            explainer = self.get_explainer(antibiotic, model, tokenizer)
            
            # Preprocess sequence
            inputs = self.preprocess_sequence(sequence, tokenizer)
            
            # Generate SHAP values
            with torch.no_grad():
                # Get model prediction first
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                pred_class = torch.argmax(probabilities, dim=-1)
                
                classes = ['S', 'I', 'R']  # Susceptible, Intermediate, Resistant
                pred_label = classes[pred_class[0].item()]
                pred_prob = probabilities[0][pred_class[0]].item()
            
            # Generate SHAP values
            shap_values = explainer.shap_values(inputs)
            
            # Process SHAP values
            if isinstance(shap_values, list):
                shap_values = np.array(shap_values)
            
            # Get token-level feature names
            tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
            feature_names = [f"token_{i}_{token}" for i, token in enumerate(tokens)]
            
            # Get base value
            base_value = explainer.expected_value
            
            # Use prediction if not provided
            if prediction is None:
                prediction = pred_label
                probability = pred_prob
            
            return SHAPExplanation(
                shap_values=shap_values,
                feature_names=feature_names,
                base_values=base_value,
                data=sequence,
                prediction=prediction,
                probability=probability,
                model_type="DNABERT",
                antibiotic=antibiotic,
                explanation_type="token_importance",
                metadata={
                    'model_path': str(self.models_dir / f"transformer_{antibiotic}"),
                    'sequence_length': len(sequence),
                    'token_count': len(tokens),
                    'max_length': inputs['input_ids'].shape[1],
                    'tokens': tokens
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating SHAP explanation for {antibiotic}: {str(e)}")
            raise
    
    def explain_batch(self,
                     antibiotic: str,
                     sequences: List[str],
                     predictions: Optional[List[str]] = None,
                     probabilities: Optional[List[float]] = None) -> List[SHAPExplanation]:
        """
        Generate SHAP explanations for a batch of sequences.
        
        Args:
            antibiotic: Antibiotic name
            sequences: List of DNA sequences
            predictions: List of predictions (optional)
            probabilities: List of probabilities (optional)
            
        Returns:
            List of SHAPExplanation objects
        """
        try:
            # Load model and tokenizer
            model, tokenizer = self.load_model_and_tokenizer(antibiotic)
            explainer = self.get_explainer(antibiotic, model, tokenizer)
            
            # Preprocess all sequences
            batch_inputs = []
            for sequence in sequences:
                inputs = self.preprocess_sequence(sequence, tokenizer)
                batch_inputs.append(inputs)
            
            explanations = []
            
            # Generate explanations for each sequence
            for i, (sequence, inputs) in enumerate(zip(sequences, batch_inputs)):
                # Get prediction if not provided
                if predictions is None or probabilities is None:
                    with torch.no_grad():
                        outputs = model(**inputs)
                        logits = outputs.logits
                        probs = torch.softmax(logits, dim=-1)
                        pred_class = torch.argmax(probs, dim=-1)
                        
                        classes = ['S', 'I', 'R']
                        pred_label = classes[pred_class[0].item()]
                        pred_prob = probs[0][pred_class[0]].item()
                        
                        if predictions is None:
                            predictions = []
                        if probabilities is None:
                            probabilities = []
                        
                        predictions.append(pred_label)
                        probabilities.append(pred_prob)
                
                # Generate SHAP values
                shap_values = explainer.shap_values(inputs)
                
                # Process SHAP values
                if isinstance(shap_values, list):
                    shap_values = np.array(shap_values)
                
                # Get tokens
                tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
                feature_names = [f"token_{i}_{token}" for i, token in enumerate(tokens)]
                
                # Get base value
                base_value = explainer.expected_value
                
                explanation = SHAPExplanation(
                    shap_values=shap_values,
                    feature_names=feature_names,
                    base_values=base_value,
                    data=sequence,
                    prediction=predictions[i],
                    probability=probabilities[i],
                    model_type="DNABERT",
                    antibiotic=antibiotic,
                    explanation_type="token_importance",
                    metadata={
                        'model_path': str(self.models_dir / f"transformer_{antibiotic}"),
                        'sequence_length': len(sequence),
                        'token_count': len(tokens),
                        'max_length': inputs['input_ids'].shape[1],
                        'tokens': tokens,
                        'batch_index': i,
                        'batch_size': len(sequences)
                    }
                )
                explanations.append(explanation)
            
            return explanations
            
        except Exception as e:
            logger.error(f"Error generating batch SHAP explanations for {antibiotic}: {str(e)}")
            raise
    
    def get_token_importance_summary(self, antibiotic: str, 
                                   sequences: List[str],
                                   top_k: int = 50) -> Dict[str, Any]:
        """
        Get token importance summary for multiple sequences.
        
        Args:
            antibiotic: Antibiotic name
            sequences: List of DNA sequences
            top_k: Number of top important tokens to return
            
        Returns:
            Dictionary with token importance statistics
        """
        try:
            explanations = self.explain_batch(antibiotic, sequences)
            
            # Collect token importance across all explanations
            token_importance = {}
            token_counts = {}
            
            for exp in explanations:
                if len(exp.shap_values.shape) > 1:
                    shap_vals = exp.shap_values[0]
                else:
                    shap_vals = exp.shap_values
                
                for i, (token_name, shap_val) in enumerate(zip(exp.feature_names, shap_vals)):
                    # Extract token from feature name
                    token = token_name.split('_', 2)[-1] if '_' in token_name else token_name
                    
                    if token not in token_importance:
                        token_importance[token] = []
                        token_counts[token] = 0
                    
                    token_importance[token].append(float(shap_val))
                    token_counts[token] += 1
            
            # Calculate statistics for each token
            token_stats = {}
            for token, values in token_importance.items():
                mean_importance = np.mean(values)
                std_importance = np.std(values)
                max_importance = np.max(values)
                min_importance = np.min(values)
                frequency = token_counts[token]
                
                token_stats[token] = {
                    'mean_importance': mean_importance,
                    'std_importance': std_importance,
                    'max_importance': max_importance,
                    'min_importance': min_importance,
                    'frequency': frequency,
                    'abs_mean_importance': abs(mean_importance)
                }
            
            # Sort by absolute mean importance
            sorted_tokens = dict(sorted(
                token_stats.items(),
                key=lambda x: x[1]['abs_mean_importance'],
                reverse=True
            ))
            
            return {
                'token_importance': sorted_tokens,
                'total_sequences': len(sequences),
                'unique_tokens': len(token_stats),
                'top_tokens': dict(list(sorted_tokens.items())[:top_k])
            }
            
        except Exception as e:
            logger.error(f"Error getting token importance summary for {antibiotic}: {str(e)}")
            raise
    
    def create_explanation_summary(self, antibiotics: List[str]) -> Dict[str, Any]:
        """
        Create a summary of explanations for multiple antibiotics.
        
        Args:
            antibiotics: List of antibiotic names
            
        Returns:
            Summary dictionary with token importance patterns
        """
        summary = {
            'antibiotics': {},
            'common_tokens': {},
            'model_types': ['DNABERT'],
            'total_models': len(antibiotics)
        }
        
        all_token_importance = {}
        
        for antibiotic in antibiotics:
            try:
                # Use sample sequences for analysis
                sample_sequences = [
                    "ATCGATCGATCGATCGATCG",
                    "GCTAGCTAGCTAGCTAGCTA",
                    "CCCCGGGGAAAATTTT"
                ]
                
                token_summary = self.get_token_importance_summary(antibiotic, sample_sequences)
                summary['antibiotics'][antibiotic] = token_summary
                
                # Collect all tokens for cross-antibiotic analysis
                for token, stats in token_summary['token_importance'].items():
                    if token not in all_token_importance:
                        all_token_importance[token] = []
                    all_token_importance[token].append(stats['mean_importance'])
                    
            except Exception as e:
                logger.warning(f"Could not process {antibiotic}: {str(e)}")
                summary['antibiotics'][antibiotic] = {'error': str(e)}
        
        # Calculate cross-antibiotic token statistics
        for token, importances in all_token_importance.items():
            if len(importances) > 1:  # Only include tokens that appear in multiple models
                summary['common_tokens'][token] = {
                    'mean_importance': np.mean(importances),
                    'std_importance': np.std(importances),
                    'max_importance': np.max(importances),
                    'min_importance': np.min(importances),
                    'frequency': len(importances)
                }
        
        # Sort common tokens by mean importance
        summary['common_tokens'] = dict(sorted(
            summary['common_tokens'].items(),
            key=lambda x: x[1]['mean_importance'],
            reverse=True
        ))
        
        return summary
