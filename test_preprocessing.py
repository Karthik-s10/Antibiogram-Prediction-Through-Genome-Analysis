"""
Test script for data preprocessing
Run this to verify the data preprocessing pipeline works correctly.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.preprocessing.data_preprocessor import DataPreprocessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test the data preprocessing pipeline."""
    
    logger.info("=" * 80)
    logger.info("Testing Data Preprocessing Pipeline")
    logger.info("=" * 80)
    
    # File paths
    phenotype_file = "DATA/BVBRC_genome_amr.txt"
    kmer_file = "DATA/SIGNIFICANT_DNA_KMERS_BACTERIA"
    rosetta_file = "DATA/BVBRC_genome.txt"
    
    # Check if files exist
    for file_path in [phenotype_file, kmer_file, rosetta_file]:
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            logger.error("Please ensure all data files are in the correct location")
            return
    
    try:
        # Initialize preprocessor
        logger.info("Initializing preprocessor...")
        preprocessor = DataPreprocessor(
            rosetta_file=rosetta_file,
            cache_dir="./data_cache"
        )
        
        # Run preprocessing
        logger.info("Starting preprocessing (this may take several minutes)...")
        X_final, Y_final = preprocessor.preprocess_data(
            phenotype_file=phenotype_file,
            kmer_file=kmer_file,
            use_cache=True,
            save_cache=True
        )
        
        # Display summary
        logger.info("=" * 80)
        logger.info("PREPROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Aligned Genomes: {len(X_final)}")
        logger.info(f"Features (K-mers): {X_final.shape[1]}")
        logger.info(f"Labels (Antibiotics): {Y_final.shape[1]}")
        logger.info(f"Antibiotics: {list(Y_final.columns)}")
        
        # Get detailed summary
        summary = preprocessor.get_data_summary(X_final, Y_final)
        logger.info(f"Feature Sparsity: {summary['feature_sparsity']:.2%}")
        
        logger.info("\nLabel Distribution (first 5 antibiotics):")
        for i, antibiotic in enumerate(list(Y_final.columns)[:5]):
            dist = summary['label_distribution'][antibiotic]
            logger.info(f"  {antibiotic}: {dist}")
        
        logger.info("=" * 80)
        logger.info("✓ Data preprocessing successful!")
        logger.info("✓ Cache saved for future use")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
