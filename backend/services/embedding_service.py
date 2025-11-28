"""
Embedding Service for Genome Sequences
Generates DNABERT embeddings (768-dim) from DNA sequences.
"""

import logging
from typing import List, Optional
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating genome embeddings using DNABERT.
    
    Converts DNA sequences into 768-dimensional vectors for similarity search.
    """
    
    MODEL_NAME = "zhihan1996/DNABERT-6"
    EMBEDDING_DIM = 768
    MAX_LENGTH = 512  # BERT max sequence length
    KMER_SIZE = 6  # DNABERT-6 uses 6-mers
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize DNABERT model and tokenizer.
        
        Args:
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device or self._detect_device()
        logger.info(f"Initializing DNABERT on device: {self.device}")
        
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _detect_device(self) -> str:
        """Detect available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _load_model(self):
        """Load DNABERT model and tokenizer."""
        try:
            logger.info(f"Loading DNABERT model: {self.MODEL_NAME}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_NAME,
                trust_remote_code=True
            )
            
            self.model = AutoModel.from_pretrained(
                self.MODEL_NAME,
                trust_remote_code=True
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("DNABERT model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load DNABERT model: {e}")
            raise
    
    def _sequence_to_kmers(self, sequence: str, k: int = 6) -> str:
        """
        Convert DNA sequence to k-mer representation for DNABERT.
        
        DNABERT expects sequences as space-separated k-mers.
        
        Args:
            sequence: DNA sequence (ACGT)
            k: K-mer size (default 6 for DNABERT-6)
            
        Returns:
            Space-separated k-mer string
        """
        # Clean sequence
        sequence = sequence.upper().replace('\n', '').replace(' ', '')
        
        # Only keep valid DNA characters
        valid_chars = set('ACGT')
        sequence = ''.join(c for c in sequence if c in valid_chars)
        
        if len(sequence) < k:
            return ""
        
        # Generate k-mers
        kmers = [sequence[i:i+k] for i in range(len(sequence) - k + 1)]
        
        return ' '.join(kmers)
    
    def embed_sequence(self, sequence: str) -> List[float]:
        """
        Generate embedding for a single DNA sequence.
        
        Args:
            sequence: DNA sequence string
            
        Returns:
            768-dimensional embedding vector
        """
        # Convert to k-mers
        kmer_sequence = self._sequence_to_kmers(sequence, self.KMER_SIZE)
        
        if not kmer_sequence:
            logger.warning("Empty sequence after k-mer conversion")
            return [0.0] * self.EMBEDDING_DIM
        
        # Tokenize
        inputs = self.tokenizer(
            kmer_sequence,
            return_tensors="pt",
            max_length=self.MAX_LENGTH,
            truncation=True,
            padding=True
        )
        
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate embedding
        with torch.no_grad():
            outputs = self.model(**inputs)
            
            # Use [CLS] token embedding (first token)
            # Shape: (1, seq_len, 768) -> (768,)
            embedding = outputs.last_hidden_state[:, 0, :].squeeze()
            
            # Convert to list
            embedding = embedding.cpu().numpy().tolist()
        
        return embedding
    
    def embed_sequences(self, sequences: List[str], batch_size: int = 8) -> List[List[float]]:
        """
        Generate embeddings for multiple DNA sequences.
        
        Args:
            sequences: List of DNA sequences
            batch_size: Batch size for processing
            
        Returns:
            List of 768-dimensional embedding vectors
        """
        logger.info(f"Generating embeddings for {len(sequences)} sequences")
        
        embeddings = []
        
        for i in range(0, len(sequences), batch_size):
            batch = sequences[i:i + batch_size]
            
            # Convert to k-mers
            kmer_sequences = [self._sequence_to_kmers(seq, self.KMER_SIZE) for seq in batch]
            
            # Filter empty sequences
            valid_indices = [j for j, ks in enumerate(kmer_sequences) if ks]
            valid_kmer_sequences = [kmer_sequences[j] for j in valid_indices]
            
            if not valid_kmer_sequences:
                # All sequences in batch were invalid
                embeddings.extend([[0.0] * self.EMBEDDING_DIM] * len(batch))
                continue
            
            # Tokenize batch
            inputs = self.tokenizer(
                valid_kmer_sequences,
                return_tensors="pt",
                max_length=self.MAX_LENGTH,
                truncation=True,
                padding=True
            )
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
            # Map back to original indices
            batch_result = [[0.0] * self.EMBEDDING_DIM] * len(batch)
            for j, valid_idx in enumerate(valid_indices):
                batch_result[valid_idx] = batch_embeddings[j].tolist()
            
            embeddings.extend(batch_result)
            
            if (i // batch_size + 1) % 10 == 0:
                logger.info(f"Processed {i + len(batch)}/{len(sequences)} sequences")
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def embed_fasta(self, fasta_content: str) -> List[float]:
        """
        Generate embedding from FASTA content.
        
        For multi-sequence FASTA, concatenates sequences before embedding.
        For very long sequences, uses sliding window and averages embeddings.
        
        Args:
            fasta_content: FASTA file content as string
            
        Returns:
            768-dimensional embedding vector
        """
        # Parse FASTA
        sequences = []
        current_seq = []
        
        for line in fasta_content.strip().split('\n'):
            if line.startswith('>'):
                if current_seq:
                    sequences.append(''.join(current_seq))
                    current_seq = []
            else:
                current_seq.append(line.strip())
        
        if current_seq:
            sequences.append(''.join(current_seq))
        
        if not sequences:
            logger.warning("No sequences found in FASTA")
            return [0.0] * self.EMBEDDING_DIM
        
        # Concatenate all sequences
        full_sequence = ''.join(sequences)
        
        # For very long sequences, use sliding window
        max_seq_length = (self.MAX_LENGTH - 2) * self.KMER_SIZE  # Account for special tokens
        
        if len(full_sequence) <= max_seq_length:
            return self.embed_sequence(full_sequence)
        
        # Sliding window for long sequences
        logger.info(f"Using sliding window for long sequence ({len(full_sequence)} bp)")
        
        window_embeddings = []
        stride = max_seq_length // 2
        
        for start in range(0, len(full_sequence), stride):
            window = full_sequence[start:start + max_seq_length]
            if len(window) >= self.KMER_SIZE:
                emb = self.embed_sequence(window)
                window_embeddings.append(emb)
        
        # Average embeddings
        if window_embeddings:
            avg_embedding = np.mean(window_embeddings, axis=0).tolist()
            return avg_embedding
        
        return [0.0] * self.EMBEDDING_DIM
    
    def embed_fasta_file(self, fasta_path: str) -> List[float]:
        """
        Generate embedding from a FASTA file.
        
        Args:
            fasta_path: Path to FASTA file
            
        Returns:
            768-dimensional embedding vector
        """
        with open(fasta_path, 'r') as f:
            content = f.read()
        
        return self.embed_fasta(content)
