"""
Large-scale data processing for hundreds of thousands of bacterial genomes.
Optimized for memory efficiency and multi-species datasets.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Iterator
import logging
from collections import defaultdict
import gc

logger = logging.getLogger(__name__)


class LargeScaleKmerProcessor:
    """
    Memory-efficient k-mer processing for very large datasets.
    Uses chunking and sparse representations.
    """
    
    def __init__(self, k: int = 10, chunk_size: int = 10000):
        """
        Initialize large-scale k-mer processor.
        
        Args:
            k: K-mer size
            chunk_size: Number of genomes to process at once (memory management)
        """
        self.k = k
        self.chunk_size = chunk_size
        self.feature_names: List[str] = []
        self.genome_ids: List[str] = []
    
    def process_kmer_file_chunked(
        self, 
        file_path: str
    ) -> Iterator[Tuple[pd.DataFrame, List[str]]]:
        """
        Process k-mer file in chunks for memory efficiency.
        
        Args:
            file_path: Path to k-mer TSV file
        
        Yields:
            Tuple of (chunk_dataframe, genome_ids_in_chunk)
        """
        logger.info(f"Processing k-mer file in chunks of {self.chunk_size}")
        
        # First pass: Count unique genomes and k-mers
        unique_genomes = set()
        unique_kmers = set()
        
        logger.info("First pass: Counting unique genomes and k-mers...")
        with open(file_path, 'r') as f:
            for i, line in enumerate(f):
                if i % 1000000 == 0 and i > 0:
                    logger.info(f"Processed {i:,} lines...")
                
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    genome_id = parts[0]
                    kmer = parts[3]
                    unique_genomes.add(genome_id)
                    unique_kmers.add(kmer)
        
        logger.info(f"Found {len(unique_genomes):,} unique genomes")
        logger.info(f"Found {len(unique_kmers):,} unique k-mers")
        
        # Store feature names (k-mers) for later use
        self.feature_names = sorted(list(unique_kmers))
        kmer_to_idx = {kmer: idx for idx, kmer in enumerate(self.feature_names)}
        
        # Second pass: Process in chunks
        genome_list = sorted(list(unique_genomes))
        self.genome_ids = genome_list
        
        for chunk_start in range(0, len(genome_list), self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, len(genome_list))
            chunk_genomes = set(genome_list[chunk_start:chunk_end])
            
            logger.info(f"Processing chunk {chunk_start:,} to {chunk_end:,}")
            
            # Build feature matrix for this chunk
            chunk_matrix = self._build_chunk_matrix(
                file_path, 
                chunk_genomes, 
                kmer_to_idx
            )
            
            # Create DataFrame
            chunk_df = pd.DataFrame(
                chunk_matrix,
                index=sorted(list(chunk_genomes)),
                columns=self.feature_names
            )
            
            yield chunk_df, sorted(list(chunk_genomes))
            
            # Clean up memory
            del chunk_matrix
            gc.collect()
    
    def _build_chunk_matrix(
        self,
        file_path: str,
        target_genomes: set,
        kmer_to_idx: Dict[str, int]
    ) -> np.ndarray:
        """Build feature matrix for a specific chunk of genomes."""
        n_genomes = len(target_genomes)
        n_kmers = len(kmer_to_idx)
        
        # Use float32 for memory efficiency
        matrix = np.zeros((n_genomes, n_kmers), dtype=np.float32)
        genome_to_idx = {g: i for i, g in enumerate(sorted(target_genomes))}
        
        # Read file and populate matrix
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 6:
                    genome_id = parts[0]
                    
                    if genome_id in target_genomes:
                        kmer = parts[3]
                        frequency = float(parts[5])  # Use prob2 as frequency
                        
                        genome_idx = genome_to_idx[genome_id]
                        kmer_idx = kmer_to_idx.get(kmer)
                        
                        if kmer_idx is not None:
                            matrix[genome_idx, kmer_idx] = frequency
        
        return matrix
    
    def get_species_distribution(
        self,
        phenotype_df: pd.DataFrame
    ) -> Dict[str, int]:
        """
        Analyze species distribution in the dataset.
        
        Args:
            phenotype_df: DataFrame with phenotype data (should have 'species' column if available)
        
        Returns:
            Dictionary mapping species to count
        """
        species_counts = defaultdict(int)
        
        # Try to infer species from genome names if species column doesn't exist
        for genome_id in phenotype_df['genome_id'].unique():
            # Common patterns: "Escherichia_coli_...", "GCA_... [Escherichia coli]"
            species = "Unknown"
            
            if '[' in genome_id and ']' in genome_id:
                species = genome_id.split('[')[1].split(']')[0]
            elif '_' in genome_id:
                parts = genome_id.split('_')
                if len(parts) >= 2:
                    species = f"{parts[0]} {parts[1]}"
            
            species_counts[species] += 1
        
        return dict(species_counts)


class MultiSpeciesTrainer:
    """
    Handles training across multiple bacterial species.
    Can create universal models or species-specific models.
    """
    
    def __init__(self):
        self.species_models: Dict[str, any] = {}
        self.universal_model: any = None
    
    def should_train_species_specific(
        self,
        species_counts: Dict[str, int],
        min_samples_per_species: int = 100
    ) -> Dict[str, bool]:
        """
        Determine which species have enough data for species-specific models.
        
        Args:
            species_counts: Dictionary mapping species to sample count
            min_samples_per_species: Minimum samples needed for species-specific model
        
        Returns:
            Dictionary mapping species to whether to train species-specific model
        """
        decisions = {}
        
        for species, count in species_counts.items():
            if count >= min_samples_per_species:
                decisions[species] = True
                logger.info(f"{species}: {count} samples → Train species-specific model")
            else:
                decisions[species] = False
                logger.info(f"{species}: {count} samples → Include in universal model only")
        
        return decisions
    
    def recommend_training_strategy(
        self,
        total_genomes: int,
        species_counts: Dict[str, int]
    ) -> str:
        """
        Recommend training strategy based on dataset characteristics.
        
        Returns:
            Strategy description
        """
        n_species = len(species_counts)
        
        if n_species == 1:
            return "SINGLE_SPECIES: Train one model for the single species"
        
        dominant_species = max(species_counts.values())
        dominant_pct = (dominant_species / total_genomes) * 100
        
        if dominant_pct > 80:
            return f"DOMINANT_SPECIES: Train species-specific model (one species is {dominant_pct:.1f}% of data)"
        
        species_with_100plus = sum(1 for c in species_counts.values() if c >= 100)
        
        if species_with_100plus >= 5:
            return f"MULTI_SPECIES_MIXED: Train {species_with_100plus} species-specific models + 1 universal model"
        
        if n_species <= 10:
            return "MULTI_SPECIES_UNIVERSAL: Train one universal model (species diversity is moderate)"
        
        return f"HIGHLY_DIVERSE: {n_species} species detected. Train universal model with species as feature"


def analyze_dataset_scale(
    kmer_file_path: str,
    phenotype_file_path: str
) -> Dict[str, any]:
    """
    Analyze dataset characteristics before training.
    Provides recommendations for training approach.
    
    Args:
        kmer_file_path: Path to k-mer TSV file
        phenotype_file_path: Path to phenotype CSV file
    
    Returns:
        Dictionary with dataset statistics and recommendations
    """
    logger.info("Analyzing dataset scale and characteristics...")
    
    # Quick scan of k-mer file
    unique_genomes = set()
    line_count = 0
    
    with open(kmer_file_path, 'r') as f:
        for line in f:
            line_count += 1
            parts = line.strip().split('\t')
            if len(parts) >= 1:
                unique_genomes.add(parts[0])
            
            if line_count % 10000000 == 0:
                logger.info(f"Scanned {line_count:,} lines...")
    
    # Load phenotype data
    phenotype_df = pd.read_csv(phenotype_file_path)
    phenotype_df.columns = phenotype_df.columns.str.strip()
    
    # Find genome column
    genome_cols = ['Genome Name', 'Genome', 'genome_id', 'Genome ID']
    genome_col = next((c for c in genome_cols if c in phenotype_df.columns), phenotype_df.columns[0])
    phenotype_df['genome_id'] = phenotype_df[genome_col]
    
    # Find antibiotic column
    antibiotic_cols = ['Antibiotic', 'antibiotic', 'Drug', 'drug']
    antibiotic_col = next((c for c in antibiotic_cols if c in phenotype_df.columns), None)
    
    antibiotics = phenotype_df[antibiotic_col].unique() if antibiotic_col else []
    
    # Analyze species distribution
    processor = LargeScaleKmerProcessor()
    species_counts = processor.get_species_distribution(phenotype_df)
    
    # Calculate statistics
    stats = {
        'total_kmer_lines': line_count,
        'unique_genomes_in_kmers': len(unique_genomes),
        'total_phenotype_records': len(phenotype_df),
        'unique_genomes_in_phenotypes': phenotype_df['genome_id'].nunique(),
        'unique_antibiotics': len(antibiotics),
        'antibiotics': list(antibiotics),
        'species_counts': species_counts,
        'n_species': len(species_counts),
    }
    
    # Estimate memory requirements
    n_genomes = len(unique_genomes)
    n_kmers_estimate = line_count / n_genomes if n_genomes > 0 else 0
    memory_gb = (n_genomes * n_kmers_estimate * 4) / (1024**3)  # float32 = 4 bytes
    
    stats['estimated_feature_matrix_size_gb'] = round(memory_gb, 2)
    
    # Get training recommendation
    trainer = MultiSpeciesTrainer()
    stats['recommended_strategy'] = trainer.recommend_training_strategy(
        n_genomes,
        species_counts
    )
    
    # Memory recommendation
    if memory_gb < 4:
        stats['memory_recommendation'] = "Standard training (< 4GB)"
    elif memory_gb < 16:
        stats['memory_recommendation'] = "Use chunked processing (4-16GB)"
    else:
        stats['memory_recommendation'] = "Use chunked processing with aggressive memory management (> 16GB)"
    
    logger.info(f"Dataset Analysis Complete:")
    logger.info(f"  - Genomes: {n_genomes:,}")
    logger.info(f"  - Antibiotics: {len(antibiotics)}")
    logger.info(f"  - Species: {len(species_counts)}")
    logger.info(f"  - Estimated size: {memory_gb:.2f} GB")
    logger.info(f"  - Strategy: {stats['recommended_strategy']}")
    
    return stats

