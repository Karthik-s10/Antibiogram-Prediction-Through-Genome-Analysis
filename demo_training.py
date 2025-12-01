"""
Demo Training Script
Demonstrates the complete training workflow without using the API.
"""

import torch  # Must import torch before other libs to avoid DLL errors
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.preprocessing.data_preprocessor import DataPreprocessor
from backend.models.xgboost_trainer import XGBoostTrainer
from backend.models.transformer_trainer import DNABERTTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run complete training workflow."""
    
    logger.info("=" * 80)
    logger.info("ANTIBIOGRAM PREDICTION - TRAINING DEMO")
    logger.info("=" * 80)
    
    # Configuration
    phenotype_file = "DATA/BVBRC_genome_amr.txt"
    kmer_file = "DATA/SIGNIFICANT_DNA_KMERS_BACTERIA"
    rosetta_file = "DATA/BVBRC_genome.txt"
    
    # Check files exist
    for file_path in [phenotype_file, kmer_file, rosetta_file]:
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            return
    
    try:
        # Step 1: Preprocess Data
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: DATA PREPROCESSING")
        logger.info("=" * 80)
        
        preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
        X_final, Y_final = preprocessor.preprocess_data(
            phenotype_file=phenotype_file,
            kmer_file=kmer_file,
            use_cache=True,
            save_cache=True
        )
        
        logger.info(f"\n✓ Data aligned successfully!")
        logger.info(f"  - Genomes: {len(X_final)}")
        logger.info(f"  - Features: {X_final.shape[1]}")
        logger.info(f"  - Antibiotics: {Y_final.shape[1]}")
        
        # Step 2: Train XGBoost
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: TRAINING XGBOOST MODEL")
        logger.info("=" * 80)
        
        xgb_trainer = XGBoostTrainer()
        
        def xgb_progress(p, msg=""):
            if int(p) % 10 == 0:
                logger.info(f"XGBoost training progress: {p:.1f}% - {msg}")
        
        # Convert DataFrames to numpy for current trainer API
        X_np = X_final.values.astype("float32")
        Y_np = Y_final.values.astype("float32")
        antibiotic_names = list(Y_final.columns)
        feature_names = list(X_final.columns)
        
        xgb_results = xgb_trainer.train_per_antibiotic(
            X=X_np,
            y=Y_np,
            antibiotic_names=antibiotic_names,
            feature_names=feature_names,
            progress_callback=xgb_progress,
        )
        
        logger.info(f"\n✓ XGBoost training complete!")
        # Aggregate simple averages from per-antibiotic metrics if available
        valid = [m for m in xgb_results.values() if 'accuracy' in m]
        if valid:
            avg_acc = sum(m['accuracy'] for m in valid) / len(valid)
            avg_f1 = sum(m['f1_macro'] for m in valid) / len(valid)
            logger.info(f"  - Approx. Average Accuracy: {avg_acc:.3f}")
            logger.info(f"  - Approx. Average F1 Score: {avg_f1:.3f}")
        logger.info(f"  - Models trained: {len(valid)}")
        logger.info(f"  - Device used: {xgb_trainer.device}")
        
        from config import settings
        xgb_path = xgb_trainer.save_models(settings.model_storage_path, "demo_xgboost_model")
        logger.info(f"  - XGBoost model saved to: {xgb_path}")
        
        # Step 3: Train DNABERT (gene-level) using new pipeline is handled via API now,
        # so we skip direct DNABERT training here to keep this demo lightweight.
        logger.info("\nSkipping direct DNABERT demo training; use API /training/transformer endpoint instead.")
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TRAINING DEMO COMPLETE - SUMMARY")
        logger.info("=" * 80)
        logger.info(f"  - Total genomes: {len(X_final)}")
        logger.info(f"  - K-mer features: {X_final.shape[1]:,}")
        logger.info(f"  - Antibiotics: {Y_final.shape[1]}")
        logger.info("\nUse the FastAPI UI or separate scripts for DNABERT training.")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\n❌ Training demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
