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
from backend.models.transformer_trainer import TransformerTrainer

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
        
        xgb_trainer = XGBoostTrainer(model_name="demo_xgboost_model")
        
        def xgb_progress(p):
            if int(p) % 10 == 0:  # Log every 10%
                logger.info(f"XGBoost training progress: {p:.1f}%")
        
        xgb_results = xgb_trainer.train(
            X=X_final,
            Y=Y_final,
            progress_callback=xgb_progress
        )
        
        logger.info(f"\n✓ XGBoost training complete!")
        logger.info(f"  - Average Accuracy: {xgb_results['avg_accuracy']:.3f}")
        logger.info(f"  - Average F1 Score: {xgb_results['avg_f1']:.3f}")
        logger.info(f"  - Models trained: {xgb_results['n_models']}")
        logger.info(f"  - Device used: {xgb_results['device']}")
        
        # Save XGBoost model
        xgb_path = xgb_trainer.save_model()
        logger.info(f"  - Model saved to: {xgb_path}")
        
        # Step 3: Train Transformer (simplified)
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: TRAINING TRANSFORMER MODEL")
        logger.info("=" * 80)
        logger.info("Note: This is a simplified/mock implementation")
        
        transformer_trainer = TransformerTrainer(model_name="demo_transformer_model")
        
        def transformer_progress(p):
            if int(p) % 10 == 0:
                logger.info(f"Transformer training progress: {p:.1f}%")
        
        transformer_results = transformer_trainer.train(
            X=X_final,
            Y=Y_final,
            progress_callback=transformer_progress,
            epochs=3
        )
        
        logger.info(f"\n✓ Transformer training complete!")
        logger.info(f"  - Average Accuracy: {transformer_results['avg_accuracy']:.3f}")
        logger.info(f"  - Average F1 Score: {transformer_results['avg_f1']:.3f}")
        logger.info(f"  - Models trained: {transformer_results['n_models']}")
        
        # Save Transformer model
        transformer_path = transformer_trainer.save_model()
        logger.info(f"  - Model saved to: {transformer_path}")
        
        # Step 4: Summary
        logger.info("\n" + "=" * 80)
        logger.info("TRAINING COMPLETE - SUMMARY")
        logger.info("=" * 80)
        
        logger.info("\n📊 Dataset:")
        logger.info(f"  - Total genomes: {len(X_final)}")
        logger.info(f"  - K-mer features: {X_final.shape[1]:,}")
        logger.info(f"  - Antibiotics: {Y_final.shape[1]}")
        logger.info(f"  - Antibiotic list: {', '.join(list(Y_final.columns)[:5])}...")
        
        logger.info("\n🤖 XGBoost Model:")
        logger.info(f"  - Accuracy: {xgb_results['avg_accuracy']:.1%}")
        logger.info(f"  - F1 Score: {xgb_results['avg_f1']:.1%}")
        logger.info(f"  - Location: {xgb_path}")
        
        logger.info("\n🧬 Transformer Model:")
        logger.info(f"  - Accuracy: {transformer_results['avg_accuracy']:.1%}")
        logger.info(f"  - F1 Score: {transformer_results['avg_f1']:.1%}")
        logger.info(f"  - Location: {transformer_path}")
        
        logger.info("\n✅ All models trained and saved successfully!")
        logger.info("=" * 80)
        
        # Display per-antibiotic results for XGBoost
        logger.info("\n📈 XGBoost Performance by Antibiotic (Top 5):")
        per_ab = xgb_results['per_antibiotic']
        for i, (antibiotic, metrics) in enumerate(list(per_ab.items())[:5]):
            logger.info(
                f"  {i+1}. {antibiotic:20s} - "
                f"Acc: {metrics['accuracy']:.3f}, "
                f"F1: {metrics['f1']:.3f}, "
                f"Samples: {metrics['n_train']+metrics['n_test']}"
            )
        
        logger.info("\n" + "=" * 80)
        logger.info("Next Steps:")
        logger.info("  1. Review model performance metrics above")
        logger.info("  2. Use trained models for predictions")
        logger.info("  3. Deploy models to production API")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
