"""
Training Job Management
Handles background training jobs for XGBoost and Transformer models.
Includes Qdrant integration for storing genome embeddings.
"""

import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback
import numpy as np

from preprocessing.data_preprocessor import DataPreprocessor
from models.xgboost_trainer import XGBoostTrainer
from models.transformer_trainer import TransformerTrainer
from jobs.job_manager import JobManager
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def store_embeddings_to_qdrant(
    X_final,
    Y_final,
    job_manager: JobManager,
    job_id: str,
    progress_start: float = 0.90,
    progress_end: float = 0.98
) -> Dict[str, Any]:
    """
    Generate DNABERT embeddings for training genomes and store in Qdrant.
    
    Args:
        X_final: Feature matrix (genomes x k-mers)
        Y_final: Label matrix (genomes x antibiotics)
        job_manager: Job manager for progress updates
        job_id: Job ID for progress updates
        progress_start: Starting progress value
        progress_end: Ending progress value
        
    Returns:
        Dict with Qdrant storage results
    """
    try:
        job_manager.update_job(
            job_id,
            progress=progress_start,
            message="Initializing Qdrant and embedding service..."
        )
        
        # Initialize services
        qdrant_service = QdrantService()
        embedding_service = EmbeddingService()
        
        # Test Qdrant connection
        if not qdrant_service.test_connection():
            logger.warning("Qdrant connection failed, skipping embedding storage")
            return {"status": "skipped", "reason": "Qdrant connection failed"}
        
        # Ensure collection exists
        qdrant_service.create_collection()
        
        all_genome_ids = list(X_final.index)
        
        # Filter out genomes that are already in Qdrant
        logger.info("Checking for existing genomes in Qdrant...")
        genome_ids = []
        skipped_count = 0
        
        for gid in all_genome_ids:
            if not qdrant_service.genome_exists(gid):
                genome_ids.append(gid)
            else:
                skipped_count += 1
        
        if skipped_count > 0:
            logger.info(f"Skipping {skipped_count} genomes already in Qdrant")
            
        if not genome_ids:
            logger.info("All genomes already exist in Qdrant. Nothing to do.")
            return {
                "status": "success",
                "genomes_stored": 0,
                "genomes_skipped": skipped_count,
                "collection_info": qdrant_service.get_collection_info()
            }
            
        n_genomes = len(genome_ids)
        
        job_manager.update_job(
            job_id,
            progress=progress_start + 0.02,
            message=f"Generating embeddings for {n_genomes} new genomes ({skipped_count} skipped)..."
        )
        
        # For k-mer based data, we'll create pseudo-embeddings from the feature vectors
        # by using a simple dimensionality reduction approach
        # In production with actual FASTA files, use embedding_service.embed_fasta()
        
        # Generate embeddings from k-mer features
        # We'll use the k-mer feature vectors and project to 768 dims
        embeddings = []
        
        # Simple approach: use random projection to reduce k-mer features to 768 dims
        # This preserves relative distances between genomes
        n_features = X_final.shape[1]
        
        if n_features > 768:
            # Random projection matrix (fixed seed for reproducibility)
            np.random.seed(42)
            projection_matrix = np.random.randn(n_features, 768) / np.sqrt(768)
            
            for i, genome_id in enumerate(genome_ids):
                feature_vector = X_final.loc[genome_id].values
                embedding = np.dot(feature_vector, projection_matrix)
                # Normalize
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                embeddings.append(embedding.tolist())
                
                if (i + 1) % 100 == 0:
                    progress = progress_start + 0.02 + ((i + 1) / n_genomes) * (progress_end - progress_start - 0.04)
                    job_manager.update_job(
                        job_id,
                        progress=progress,
                        message=f"Generated embeddings: {i + 1}/{n_genomes}"
                    )
        else:
            # Pad to 768 dims if fewer features
            for i, genome_id in enumerate(genome_ids):
                feature_vector = X_final.loc[genome_id].values
                embedding = np.zeros(768)
                embedding[:n_features] = feature_vector
                # Normalize
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                embeddings.append(embedding.tolist())
        
        job_manager.update_job(
            job_id,
            progress=progress_end - 0.02,
            message="Uploading embeddings to Qdrant..."
        )
        
        # Prepare metadata (antibiotic labels for each genome)
        metadata = []
        for genome_id in genome_ids:
            labels = Y_final.loc[genome_id].to_dict()
            # Convert NaN to None for JSON serialization
            labels = {k: (int(v) if not np.isnan(v) else None) for k, v in labels.items()}
            metadata.append({
                "antibiotic_labels": labels,
                "n_antibiotics_tested": sum(1 for v in labels.values() if v is not None)
            })
        
        # Upsert to Qdrant
        qdrant_service.upsert_genomes(
            genome_ids=genome_ids,
            embeddings=embeddings,
            metadata=metadata
        )
        
        # Get collection info
        collection_info = qdrant_service.get_collection_info()
        
        logger.info(f"Successfully stored {n_genomes} genome embeddings in Qdrant")
        
        return {
            "status": "success",
            "genomes_stored": n_genomes,
            "genomes_skipped": skipped_count,
            "collection_info": collection_info
        }
        
    except Exception as e:
        logger.error(f"Failed to store embeddings in Qdrant: {e}")
        logger.error(traceback.format_exc())
        return {
            "status": "failed",
            "error": str(e)
        }


def train_xgboost_job(
    job_id: str,
    phenotype_file: str,
    kmer_file: str,
    rosetta_file: str,
    job_manager: JobManager,
    model_name: str = "xgboost_amr_model",
    **kwargs
) -> None:
    """
    Background job for training XGBoost model.
    
    Args:
        job_id: Unique job identifier
        phenotype_file: Path to phenotype data
        kmer_file: Path to k-mer data
        rosetta_file: Path to ID mapping file
        job_manager: Job manager instance
        model_name: Name for the trained model
        **kwargs: Additional training parameters
    """
    try:
        job_manager.update_job(job_id, status="running", progress=0.0)
        logger.info(f"Starting XGBoost training job {job_id}")
        
        # Step 1: Preprocess data (0-50% progress)
        job_manager.update_job(
            job_id,
            progress=0.05,
            message="Initializing data preprocessor..."
        )
        
        preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
        
        job_manager.update_job(
            job_id,
            progress=0.10,
            message="Loading and aligning data (this may take several minutes)..."
        )
        
        X_final, Y_final = preprocessor.preprocess_data(
            phenotype_file=phenotype_file,
            kmer_file=kmer_file,
            use_cache=True,
            save_cache=True
        )
        
        job_manager.update_job(
            job_id,
            progress=0.50,
            message=f"Data aligned: {len(X_final)} genomes, {X_final.shape[1]} features, {Y_final.shape[1]} antibiotics"
        )
        
        # Step 2: Train XGBoost model (50-100% progress)
        job_manager.update_job(
            job_id,
            progress=0.55,
            message="Initializing XGBoost trainer..."
        )
        
        trainer = XGBoostTrainer(model_name=model_name)
        
        job_manager.update_job(
            job_id,
            progress=0.60,
            message="Training XGBoost model (GPU detection in progress)..."
        )
        
        results = trainer.train(
            X=X_final,
            Y=Y_final,
            progress_callback=lambda p: job_manager.update_job(
                job_id,
                progress=0.60 + (p * 0.35),  # Map 0-100% to 60-95%
                message=f"Training XGBoost: {p:.1f}% complete"
            )
        )
        
        job_manager.update_job(
            job_id,
            progress=0.95,
            message="Saving model..."
        )
        
        # Save model
        model_path = trainer.save_model()
        
        # Complete job
        job_manager.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message="Training completed successfully",
            result={
                "model_type": "xgboost",
                "model_path": str(model_path),
                "metrics": results,
                "n_genomes": len(X_final),
                "n_features": X_final.shape[1],
                "n_antibiotics": Y_final.shape[1],
                "antibiotics": list(Y_final.columns)
            }
        )
        
        logger.info(f"XGBoost training job {job_id} completed successfully")
        
    except Exception as e:
        error_msg = f"XGBoost training failed: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        job_manager.update_job(
            job_id,
            status="failed",
            message=error_msg,
            error=str(e)
        )


def train_transformer_job(
    job_id: str,
    phenotype_file: str,
    kmer_file: str,
    rosetta_file: str,
    job_manager: JobManager,
    model_name: str = "dnabert_amr_model",
    **kwargs
) -> None:
    """
    Background job for training Transformer (DNABERT) model.
    
    Args:
        job_id: Unique job identifier
        phenotype_file: Path to phenotype data
        kmer_file: Path to k-mer data
        rosetta_file: Path to ID mapping file
        job_manager: Job manager instance
        model_name: Name for the trained model
        **kwargs: Additional training parameters
    """
    try:
        job_manager.update_job(job_id, status="running", progress=0.0)
        logger.info(f"Starting Transformer training job {job_id}")
        
        # Step 1: Preprocess data (0-50% progress)
        job_manager.update_job(
            job_id,
            progress=0.05,
            message="Initializing data preprocessor..."
        )
        
        preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
        
        job_manager.update_job(
            job_id,
            progress=0.10,
            message="Loading and aligning data (this may take several minutes)..."
        )
        
        X_final, Y_final = preprocessor.preprocess_data(
            phenotype_file=phenotype_file,
            kmer_file=kmer_file,
            use_cache=True,
            save_cache=True
        )
        
        job_manager.update_job(
            job_id,
            progress=0.50,
            message=f"Data aligned: {len(X_final)} genomes, {X_final.shape[1]} features, {Y_final.shape[1]} antibiotics"
        )
        
        # Step 2: Train Transformer model (50-100% progress)
        job_manager.update_job(
            job_id,
            progress=0.55,
            message="Initializing Transformer trainer..."
        )
        
        trainer = TransformerTrainer(model_name=model_name)
        
        job_manager.update_job(
            job_id,
            progress=0.60,
            message="Training Transformer model (GPU detection in progress)..."
        )
        
        results = trainer.train(
            X=X_final,
            Y=Y_final,
            progress_callback=lambda p: job_manager.update_job(
                job_id,
                progress=0.60 + (p * 0.35),  # Map 0-100% to 60-95%
                message=f"Training Transformer: {p:.1f}% complete"
            )
        )
        
        job_manager.update_job(
            job_id,
            progress=0.95,
            message="Saving model..."
        )
        
        # Save model
        model_path = trainer.save_model()
        
        # Complete job
        job_manager.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message="Training completed successfully",
            result={
                "model_type": "transformer",
                "model_path": str(model_path),
                "metrics": results,
                "n_genomes": len(X_final),
                "n_features": X_final.shape[1],
                "n_antibiotics": Y_final.shape[1],
                "antibiotics": list(Y_final.columns)
            }
        )
        
        logger.info(f"Transformer training job {job_id} completed successfully")
        
    except Exception as e:
        error_msg = f"Transformer training failed: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        job_manager.update_job(
            job_id,
            status="failed",
            message=error_msg,
            error=str(e)
        )


def train_parallel_job(
    job_id: str,
    phenotype_file: str,
    kmer_file: str,
    rosetta_file: str,
    job_manager: JobManager,
    xgboost_model_name: str = "xgboost_amr_model",
    transformer_model_name: str = "dnabert_amr_model",
    **kwargs
) -> None:
    """
    Background job for training both XGBoost and Transformer models in parallel.
    
    Args:
        job_id: Unique job identifier
        phenotype_file: Path to phenotype data
        kmer_file: Path to k-mer data
        rosetta_file: Path to ID mapping file
        job_manager: Job manager instance
        xgboost_model_name: Name for XGBoost model
        transformer_model_name: Name for Transformer model
        **kwargs: Additional training parameters
    """
    try:
        job_manager.update_job(job_id, status="running", progress=0.0)
        logger.info(f"Starting parallel training job {job_id}")
        
        # Step 1: Preprocess data once (0-40% progress)
        job_manager.update_job(
            job_id,
            progress=0.05,
            message="Initializing data preprocessor..."
        )
        
        preprocessor = DataPreprocessor(rosetta_file=rosetta_file)
        
        job_manager.update_job(
            job_id,
            progress=0.10,
            message="Loading and aligning data (this may take several minutes)..."
        )
        
        X_final, Y_final = preprocessor.preprocess_data(
            phenotype_file=phenotype_file,
            kmer_file=kmer_file,
            use_cache=True,
            save_cache=True
        )
        
        job_manager.update_job(
            job_id,
            progress=0.40,
            message=f"Data aligned: {len(X_final)} genomes, {X_final.shape[1]} features, {Y_final.shape[1]} antibiotics"
        )
        
        # Step 2: Train both models in parallel (40-100% progress)
        xgboost_results = {}
        transformer_results = {}
        xgboost_error = None
        transformer_error = None
        
        def train_xgboost_thread():
            nonlocal xgboost_results, xgboost_error
            try:
                job_manager.update_job(
                    job_id,
                    progress=0.45,
                    message="Training XGBoost model..."
                )
                
                trainer = XGBoostTrainer(model_name=xgboost_model_name)
                results = trainer.train(X=X_final, Y=Y_final)
                model_path = trainer.save_model()
                
                xgboost_results = {
                    "model_type": "xgboost",
                    "model_path": str(model_path),
                    "metrics": results
                }
            except Exception as e:
                xgboost_error = str(e)
                logger.error(f"XGBoost training failed: {e}")
                logger.error(traceback.format_exc())
        
        def train_transformer_thread():
            nonlocal transformer_results, transformer_error
            try:
                job_manager.update_job(
                    job_id,
                    progress=0.45,
                    message="Training Transformer model..."
                )
                
                trainer = TransformerTrainer(model_name=transformer_model_name)
                results = trainer.train(X=X_final, Y=Y_final)
                model_path = trainer.save_model()
                
                transformer_results = {
                    "model_type": "transformer",
                    "model_path": str(model_path),
                    "metrics": results
                }
            except Exception as e:
                transformer_error = str(e)
                logger.error(f"Transformer training failed: {e}")
                logger.error(traceback.format_exc())
        
        # Start both training threads
        xgboost_thread = threading.Thread(target=train_xgboost_thread)
        transformer_thread = threading.Thread(target=train_transformer_thread)
        
        xgboost_thread.start()
        transformer_thread.start()
        
        # Wait for both to complete
        xgboost_thread.join()
        transformer_thread.join()
        
        job_manager.update_job(
            job_id,
            progress=0.85,
            message="Both models trained, storing embeddings to Qdrant..."
        )
        
        # Check for errors
        if xgboost_error and transformer_error:
            raise Exception(
                f"Both models failed. XGBoost: {xgboost_error}, Transformer: {transformer_error}"
            )
        elif xgboost_error:
            logger.warning(f"XGBoost failed but Transformer succeeded: {xgboost_error}")
        elif transformer_error:
            logger.warning(f"Transformer failed but XGBoost succeeded: {transformer_error}")
        
        # Step 3: Store embeddings to Qdrant (85-98% progress)
        qdrant_result = store_embeddings_to_qdrant(
            X_final=X_final,
            Y_final=Y_final,
            job_manager=job_manager,
            job_id=job_id,
            progress_start=0.85,
            progress_end=0.98
        )
        
        # Complete job
        job_manager.update_job(
            job_id,
            status="completed",
            progress=1.0,
            message="Parallel training completed",
            result={
                "xgboost": xgboost_results if not xgboost_error else {"error": xgboost_error},
                "transformer": transformer_results if not transformer_error else {"error": transformer_error},
                "qdrant": qdrant_result,
                "n_genomes": len(X_final),
                "n_features": X_final.shape[1],
                "n_antibiotics": Y_final.shape[1],
                "antibiotics": list(Y_final.columns)
            }
        )
        
        logger.info(f"Parallel training job {job_id} completed")
        
    except Exception as e:
        error_msg = f"Parallel training failed: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        job_manager.update_job(
            job_id,
            status="failed",
            message=error_msg,
            error=str(e)
        )
