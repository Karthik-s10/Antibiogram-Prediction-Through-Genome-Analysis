"""
Attention Visualization Service

Handles attention weight extraction and visualization for DNABERT models.
"""
import numpy as np
import torch
from typing import List, Dict, Optional
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import logging

logger = logging.getLogger(__name__)

class AttentionVisualizer:
    """Handles attention visualization for DNABERT models."""
    
    def __init__(self, model_path: str, max_length: int = 512):
        """
        Initialize the attention visualizer.
        
        Args:
            model_path: Path to the trained DNABERT model
            max_length: Maximum sequence length
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.max_length = max_length
        self.model.to(self.device)
        self.model.eval()
        
    def get_attention(self, sequence: str) -> Dict:
        """
        Get attention weights for the given DNA sequence.
        
        Args:
            sequence: Input DNA sequence
            
        Returns:
            Dictionary containing attention weights and tokens
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                sequence,
                return_tensors="pt",
                max_length=self.max_length,
                padding="max_length",
                truncation=True
            ).to(self.device)
            
            # Get attention weights
            with torch.no_grad():
                outputs = self.model(
                    **inputs,
                    output_attentions=True,
                    return_dict=True
                )
                
            # Get attention from all layers and heads
            attentions = torch.stack(outputs.attentions).squeeze(1).cpu().numpy()
            
            # Convert to list for JSON serialization
            attentions = [
                layer.tolist()  # [heads, seq_len, seq_len]
                for layer in attentions
            ]
            
            # Get tokens
            tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0].cpu().numpy())
            
            return {
                "attention": attentions,
                "tokens": tokens,
                "sequence": sequence
            }
            
        except Exception as e:
            logger.error(f"Error getting attention: {str(e)}")
            raise RuntimeError(f"Failed to get attention: {str(e)}")
