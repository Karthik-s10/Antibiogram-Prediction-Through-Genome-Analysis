"""
K-mer feature extraction and processing.
Converts k-mer frequency data into feature matrices for ML models.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from io import StringIO, BytesIO
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class KmerProcessor:
    """
    Processes k-mer data into feature matrices.
    Handles both k=10 (XGBoost) and k=6 (DNABERT) data.
    """
    
    def __init__(self, k: int = 10):
        """
        Initialize k-mer processor.
        
        Args:
            k: K-mer size (10 for XGBoost, 6 for DNABERT)
        """
        self.k = k
        self.feature_names: List[str] = []
        self.genome_ids: List[str] = []
    
    @staticmethod
    def detect_k_from_file(content: bytes) -> int:
        """
        Auto-detect k-mer size from file by examining the first few entries.
        
        Args:
            content: Raw file content in bytes
        
        Returns:
            Detected k-mer size
        """
        try:
            text_content = content.decode('utf-8')
            lines = text_content.strip().split('\n')
            
            # Try to find k from file format (column 3)
            for line in lines[:100]:  # Check first 100 lines
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    try:
                        k_from_file = int(parts[2])
                        logger.info(f"Auto-detected k-mer size from file: k={k_from_file}")
                        return k_from_file
                    except (ValueError, IndexError):
                        pass
                    
                    # Alternative: detect from k-mer sequence length
                    kmer_seq = parts[3]
                    if kmer_seq and all(c in 'ACGTN' for c in kmer_seq.upper()):
                        k_detected = len(kmer_seq)
                        logger.info(f"Auto-detected k-mer size from sequence length: k={k_detected}")
                        return k_detected
            
            # Default fallback
            logger.warning("Could not auto-detect k-mer size, defaulting to k=10")
            return 10
            
        except Exception as e:
            logger.error(f"Error detecting k-mer size: {e}")
            return 10
    
    def parse_kmer_file(self, content: bytes, auto_detect_k: bool = False) -> pd.DataFrame:
        """
        Parse k-mer TSV file.
        
        Expected format:
        GCA_000002515.1 Bacteria 10 ACCCCGCGCG 1.43e-07 9.83e-03
        
        Columns: genome_id, domain, k, kmer_sequence, prob1, prob2
        
        Args:
            content: Raw file content in bytes
            auto_detect_k: If True, auto-detect k from file and update self.k
        
        Returns:
            DataFrame with parsed k-mer data
        """
        try:
            # Auto-detect k if requested
            if auto_detect_k:
                detected_k = self.detect_k_from_file(content)
                self.k = detected_k
                logger.info(f"Using auto-detected k-mer size: k={self.k}")
            
            # Decode content
            text_content = content.decode('utf-8')

            # Detect number of columns from first non-empty line to support both
            # legacy 6-column format and new 5-column (single-probability) format.
            lines = [ln for ln in text_content.split('\n') if ln.strip()]
            if not lines:
                raise ValueError("Empty k-mer file")
            first_line = lines[0]
            n_cols = len(first_line.split('\t'))

            if n_cols == 5:
                col_names = ['genome_id', 'domain', 'k', 'kmer_sequence', 'prob']
            else:
                col_names = ['genome_id', 'domain', 'k', 'kmer_sequence', 'prob1', 'prob2']

            # Read as tab-separated
            df = pd.read_csv(
                StringIO(text_content),
                sep='\t',
                header=None,
                names=col_names
            )

            # Normalize probability columns so that downstream code can always use
            # either prob2 (preferred) or a single 'prob' column.
            if 'prob2' not in df.columns:
                if 'prob' in df.columns:
                    df['prob2'] = df['prob']
                elif 'prob1' in df.columns:
                    df['prob2'] = df['prob1']

            # Ensure genome IDs are stored as strings for consistent alignment with
            # phenotype data (which uses Taxon ID / Genome ID as strings).
            if 'genome_id' in df.columns:
                df['genome_id'] = df['genome_id'].astype(str).str.strip()
            
            # Filter by k-mer size if specified
            if 'k' in df.columns:
                df = df[df['k'] == self.k]
            
            logger.info(f"Parsed {len(df)} k-mer entries from file (k={self.k})")
            logger.info(f"Unique genomes: {df['genome_id'].nunique()}")
            logger.info(f"Unique k-mers: {df['kmer_sequence'].nunique()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing k-mer file: {e}", exc_info=True)
            raise ValueError(f"Failed to parse k-mer file: {str(e)}")
    
    def build_feature_matrix(self, kmer_df: pd.DataFrame) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Build feature matrix from k-mer dataframe.
        
        Args:
            kmer_df: DataFrame with k-mer data
        
        Returns:
            Tuple of (feature_matrix, genome_ids, feature_names)
            - feature_matrix: numpy array (n_genomes × n_kmers)
            - genome_ids: list of genome identifiers
            - feature_names: list of k-mer sequences
        """
        import time
        
        t_start = time.time()
        
        # Get unique genomes and k-mers
        logger.info("Building feature matrix: extracting unique genomes...")
        genome_ids = sorted(kmer_df['genome_id'].unique())
        n_genomes = len(genome_ids)
        logger.info(f"  Found {n_genomes:,} unique genomes")
        
        logger.info("Building feature matrix: extracting unique k-mers...")
        kmer_sequences = sorted(kmer_df['kmer_sequence'].unique())
        n_kmers = len(kmer_sequences)
        logger.info(f"  Found {n_kmers:,} unique k-mers")

        # Choose probability column to use as the frequency/score.
        if 'prob2' in kmer_df.columns:
            value_col = 'prob2'
        elif 'prob' in kmer_df.columns:
            value_col = 'prob'
        else:
            value_col = 'prob1'
        logger.info(f"  Using '{value_col}' as probability column")

        # Use vectorized pivot instead of slow row-by-row iteration
        logger.info("Building feature matrix: pivoting data (this may take a few minutes)...")
        t_pivot = time.time()
        
        # Create genome and kmer index mappings for fast lookup
        genome_to_idx = {g: i for i, g in enumerate(genome_ids)}
        kmer_to_idx = {k: i for i, k in enumerate(kmer_sequences)}
        
        # Pre-allocate matrix
        feature_matrix = np.zeros((n_genomes, n_kmers), dtype=np.float32)
        
        # Vectorized approach: map genome_id and kmer_sequence to indices
        logger.info("  Mapping genome IDs to row indices...")
        row_indices = kmer_df['genome_id'].map(genome_to_idx).values
        
        logger.info("  Mapping k-mer sequences to column indices...")
        col_indices = kmer_df['kmer_sequence'].map(kmer_to_idx).values
        
        logger.info("  Extracting probability values...")
        values = kmer_df[value_col].values.astype(np.float32)
        
        # Fill matrix using advanced indexing (much faster than loops)
        logger.info(f"  Filling {n_genomes:,} x {n_kmers:,} matrix with {len(values):,} values...")
        feature_matrix[row_indices, col_indices] = values
        
        t_pivot_elapsed = time.time() - t_pivot
        logger.info(f"  Pivot completed in {t_pivot_elapsed:.1f}s")
        
        # Store for later use
        self.genome_ids = genome_ids
        self.feature_names = kmer_sequences
        
        t_total = time.time() - t_start
        logger.info(f"Built feature matrix: {feature_matrix.shape} in {t_total:.1f}s")
        logger.info(f"Sparsity: {(feature_matrix == 0).sum() / feature_matrix.size * 100:.2f}%")
        
        return feature_matrix, genome_ids, kmer_sequences
    
    def extract_kmers_from_fasta(self, fasta_content: str) -> Dict[str, int]:
        """
        Extract k-mer frequencies from a FASTA sequence.
        Used for prediction on new genomes.
        
        Args:
            fasta_content: FASTA format string
        
        Returns:
            Dictionary mapping k-mer to count
        """
        # Parse FASTA
        lines = fasta_content.strip().split('\n')
        sequence = ''.join(line.strip() for line in lines if not line.startswith('>'))
        sequence = sequence.upper()
        
        # Count k-mers
        kmer_counts = defaultdict(int)
        for i in range(len(sequence) - self.k + 1):
            kmer = sequence[i:i+self.k]
            # Only count k-mers with valid nucleotides
            if all(base in 'ACGT' for base in kmer):
                kmer_counts[kmer] += 1
        
        return dict(kmer_counts)
    
    def kmer_counts_to_feature_vector(
        self,
        kmer_counts: Dict[str, int],
        feature_names: List[str]
    ) -> np.ndarray:
        """
        Convert k-mer counts to feature vector matching training data format.
        
        Args:
            kmer_counts: Dictionary of k-mer counts
            feature_names: List of k-mer features from training
        
        Returns:
            Feature vector as numpy array
        """
        feature_vector = np.zeros(len(feature_names), dtype=np.float32)
        
        total_kmers = sum(kmer_counts.values())
        for i, kmer in enumerate(feature_names):
            if kmer in kmer_counts:
                # Normalize to frequency
                feature_vector[i] = kmer_counts[kmer] / total_kmers if total_kmers > 0 else 0
        
        return feature_vector
    
    def save_feature_info(self, filepath: str):
        """
        Save feature names and genome IDs for later use.
        
        Args:
            filepath: Path to save JSON file
        """
        import json
        
        info = {
            'k': self.k,
            'n_features': len(self.feature_names),
            'n_genomes': len(self.genome_ids),
            'feature_names': self.feature_names,
            'genome_ids': self.genome_ids
        }
        
        with open(filepath, 'w') as f:
            json.dump(info, f)
        
        logger.info(f"Saved feature info to {filepath}")
    
    def load_feature_info(self, filepath: str):
        """
        Load feature names and genome IDs from saved file.
        
        Args:
            filepath: Path to JSON file
        """
        import json
        
        with open(filepath, 'r') as f:
            info = json.load(f)
        
        self.k = info['k']
        self.feature_names = info['feature_names']
        self.genome_ids = info['genome_ids']
        
        logger.info(f"Loaded feature info from {filepath}: {len(self.feature_names)} features")

