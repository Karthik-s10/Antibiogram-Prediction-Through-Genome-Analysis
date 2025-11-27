"""
Training job implementations for XGBoost and Transformer models.
Executes training pipelines as background tasks.
"""
import logging
import traceback
from typing import Optional
import numpy as np

from jobs.job_manager import JobManager, JobStatus
from preprocessing.kmer_processor import KmerProcessor
from preprocessing.phenotype_parser import PhenotypeParser
from models.xgboost_trainer import XGBoostTrainer
from services.qdrant_service import QdrantService
from config import settings

logger = logging.getLogger(__name__)


def _generate_embeddings_from_features(feature_matrix: np.ndarray, target_dim: int = 768) -> np.ndarray:
    """
    Generate embeddings from feature matrix using PCA to reduce dimensions.
    
    Args:
        feature_matrix: Feature matrix (n_genomes × n_features)
        target_dim: Target embedding dimension (default: 768 for Qdrant)
    
    Returns:
        Embeddings array (n_genomes × target_dim)
    """
    try:
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        
        n_genomes, n_features = feature_matrix.shape
        
        # If already at or below target dimension, just pad/truncate
        if n_features <= target_dim:
            # Pad with zeros if needed
            if n_features < target_dim:
                padding = np.zeros((n_genomes, target_dim - n_features))
                embeddings = np.hstack([feature_matrix, padding])
            else:
                embeddings = feature_matrix
        else:
            # Use PCA to reduce dimensions
            logger.info(f"Reducing features from {n_features} to {target_dim} dimensions using PCA...")
            
            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(feature_matrix)
            
            # Apply PCA
            pca = PCA(n_components=min(target_dim, n_genomes - 1))  # Can't have more components than samples
            embeddings = pca.fit_transform(X_scaled)
            
            # If PCA produced fewer components, pad with zeros
            if embeddings.shape[1] < target_dim:
                padding = np.zeros((n_genomes, target_dim - embeddings.shape[1]))
                embeddings = np.hstack([embeddings, padding])
            
            explained_variance = pca.explained_variance_ratio_.sum()
            logger.info(f"PCA explained variance: {explained_variance:.2%}")
        
        # Normalize embeddings to unit length for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        embeddings = embeddings / norms
        
        return embeddings.astype(np.float32)
        
    except ImportError:
        # Fallback: simple truncation/padding if sklearn not available
        logger.warning("sklearn not available, using simple truncation/padding for embeddings")
        n_genomes, n_features = feature_matrix.shape
        
        if n_features >= target_dim:
            embeddings = feature_matrix[:, :target_dim]
        else:
            padding = np.zeros((n_genomes, target_dim - n_features))
            embeddings = np.hstack([feature_matrix, padding])
        
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings = embeddings / norms
        
        return embeddings.astype(np.float32)
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        # Fallback: return zero-padded feature matrix
        n_genomes, n_features = feature_matrix.shape
        if n_features >= target_dim:
            return feature_matrix[:, :target_dim].astype(np.float32)
        else:
            padding = np.zeros((n_genomes, target_dim - n_features))
            return np.hstack([feature_matrix, padding]).astype(np.float32)


def train_xgboost_job(
    job_id: str,
    kmer_content: bytes,
    phenotype_content: bytes,
    model_name: str,
    max_depth: int,
    learning_rate: float,
    n_estimators: int,
    k: int,
    job_manager: JobManager
):
    """
    Execute XGBoost training as a background job.
    
    Args:
        job_id: Unique job identifier
        kmer_content: Raw k-mer file content
        phenotype_content: Raw phenotype file content
        model_name: Name for the trained model
        max_depth: XGBoost max tree depth
        learning_rate: XGBoost learning rate
        n_estimators: Number of boosting rounds
        job_manager: JobManager instance for status updates
    """
    try:
        # Update status to running
        job_manager.update_job(
            job_id,
            status=JobStatus.RUNNING,
            progress=0,
            current_step="Starting XGBoost training pipeline..."
        )
        
        # Step 1: Parse k-mer data
        logger.info(f"[{job_id}] Parsing k-mer data with k={k}...")
        job_manager.update_job(
            job_id,
            progress=5,
            current_step=f"Parsing k-mer data (k={k})..."
        )
        
        kmer_processor = KmerProcessor(k=k)
        kmer_df = kmer_processor.parse_kmer_file(kmer_content)
        
        # Step 2: Build feature matrix
        logger.info(f"[{job_id}] Building feature matrix...")
        job_manager.update_job(
            job_id,
            progress=10,
            current_step="Building feature matrix..."
        )
        
        X, feature_genome_ids, feature_names = kmer_processor.build_feature_matrix(kmer_df)
        
        # Step 3: Parse phenotype data
        logger.info(f"[{job_id}] Parsing phenotype data...")
        job_manager.update_job(
            job_id,
            progress=15,
            current_step="Parsing phenotype data..."
        )
        
        phenotype_parser = PhenotypeParser()
        phenotype_df = phenotype_parser.parse_phenotype_file(phenotype_content)
        
        # Step 4: Align data
        logger.info(f"[{job_id}] Aligning feature and label data...")
        job_manager.update_job(
            job_id,
            progress=20,
            current_step="Aligning feature and label matrices..."
        )
        
        aligned_genome_ids, y, antibiotic_names = phenotype_parser.align_data(
            feature_genome_ids,
            phenotype_df
        )
        
        # Filter X to only include aligned genomes
        genome_id_to_idx = {gid: i for i, gid in enumerate(feature_genome_ids)}
        aligned_indices = [genome_id_to_idx[gid] for gid in aligned_genome_ids]
        X_aligned = X[aligned_indices]
        
        logger.info(f"[{job_id}] Training data: {X_aligned.shape[0]} genomes, "
                   f"{X_aligned.shape[1]} features, {len(antibiotic_names)} antibiotics")
        
        # Step 4.5: Store embeddings in Qdrant for similarity search
        logger.info(f"[{job_id}] Storing genome embeddings in Qdrant...")
        job_manager.update_job(
            job_id,
            progress=22,
            current_step="Storing genome embeddings in vector database..."
        )
        try:
            qdrant_service = QdrantService()
            if qdrant_service.client:
                # Generate embeddings from feature vectors using PCA to reduce to 768 dimensions
                embeddings = _generate_embeddings_from_features(X_aligned, target_dim=768)
                
                # Prepare metadata for each genome
                metadata_list = []
                for genome_idx, genome_id in enumerate(aligned_genome_ids):
                    # Get resistance profile for this genome
                    resistance_profile = {}
                    for i, antibiotic in enumerate(antibiotic_names):
                        label = y[genome_idx, i]
                        if label != -1:  # Only include if label exists
                            resistance_map = {0: 'S', 1: 'I', 2: 'R'}
                            resistance_profile[antibiotic] = resistance_map.get(label, 'Unknown')
                    
                    metadata_list.append({
                        'model_name': model_name,
                        'model_type': 'xgboost',
                        'k': k,
                        'resistance_profile': resistance_profile,
                        'n_antibiotics': len(antibiotic_names)
                    })
                
                # Batch insert embeddings
                inserted_count = qdrant_service.batch_insert_embeddings(
                    genome_ids=aligned_genome_ids,
                    embeddings=embeddings,
                    metadata_list=metadata_list
                )
                logger.info(f"[{job_id}] ✅ Stored {inserted_count} genome embeddings in Qdrant")
            else:
                logger.warning(f"[{job_id}] ⚠️  Qdrant not available, skipping embedding storage")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store embeddings in Qdrant (non-critical): {e}")
            # Continue training even if Qdrant fails
        
        # Step 5: Train models
        logger.info(f"[{job_id}] Training XGBoost models...")
        job_manager.update_job(
            job_id,
            progress=25,
            current_step="Training XGBoost models for each antibiotic..."
        )
        
        # Check if job was cancelled before starting training
        job = job_manager.get_job(job_id)
        if job and job.status == JobStatus.CANCELLED:
            logger.info(f"[{job_id}] Training cancelled before model training")
            return
        
        def progress_callback(progress, message):
            # Check for cancellation during training
            job = job_manager.get_job(job_id)
            if job and job.status == JobStatus.CANCELLED:
                raise InterruptedError("Training job was cancelled by user")
            job_manager.update_job(job_id, progress=progress, current_step=message)
        
        logger.info(f"[{job_id}] Initializing XGBoost trainer with GPU support...")
        trainer = XGBoostTrainer(
            max_depth=max_depth,
            learning_rate=learning_rate,
            n_estimators=n_estimators,
            use_gpu=True  # Always prioritize GPU
        )
        if trainer.device == 'cuda':
            logger.info(f"[{job_id}] ✅ XGBoost will use GPU for training")
        else:
            logger.warning(f"[{job_id}] ⚠️  XGBoost will use CPU (GPU not available)")
        
        try:
            metrics = trainer.train_per_antibiotic(
                X_aligned,
                y,
                antibiotic_names,
                feature_names,
                progress_callback=progress_callback
            )
        except InterruptedError:
            logger.info(f"[{job_id}] Training cancelled during model training")
            job_manager.update_job(
                job_id,
                status=JobStatus.CANCELLED,
                current_step="Training cancelled by user"
            )
            return
        
        # Check for cancellation before saving
        job = job_manager.get_job(job_id)
        if job and job.status == JobStatus.CANCELLED:
            logger.info(f"[{job_id}] Training cancelled, skipping model save")
            return
        
        # Step 6: Save models
        logger.info(f"[{job_id}] Saving trained models...")
        job_manager.update_job(
            job_id,
            progress=90,
            current_step="Saving trained models..."
        )
        
        model_path = trainer.save_models(settings.model_storage_path, model_name)
        
        # Save feature info
        feature_info_path = f"{settings.model_storage_path}/{model_name}_features.json"
        kmer_processor.save_feature_info(feature_info_path)
        
        # Step 7: Calculate summary metrics
        logger.info(f"[{job_id}] Computing summary metrics...")
        job_manager.update_job(
            job_id,
            progress=95,
            current_step="Computing summary metrics..."
        )
        
        # Aggregate metrics
        successful_models = [k for k, v in metrics.items() if 'error' not in v]
        avg_accuracy = sum(m['accuracy'] for k, m in metrics.items() if 'error' not in m) / max(len(successful_models), 1)
        avg_f1 = sum(m['f1_macro'] for k, m in metrics.items() if 'error' not in m) / max(len(successful_models), 1)
        avg_jaccard = sum(m['jaccard_macro'] for k, m in metrics.items() if 'error' not in m) / max(len(successful_models), 1)
        
        summary_metrics = {
            'model_type': 'xgboost',
            'model_name': model_name,
            'model_path': model_path,
            'n_genomes': X_aligned.shape[0],
            'n_features': X_aligned.shape[1],
            'n_antibiotics': len(antibiotic_names),
            'n_successful_models': len(successful_models),
            'antibiotics': antibiotic_names,
            'avg_accuracy': float(avg_accuracy),
            'avg_f1_macro': float(avg_f1),
            'avg_jaccard_macro': float(avg_jaccard),
            'per_antibiotic_metrics': metrics
        }
        
        # Complete job
        logger.info(f"[{job_id}] Training completed successfully!")
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            current_step="Training completed successfully!",
            metrics=summary_metrics
        )
        
    except Exception as e:
        error_msg = f"Training failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"[{job_id}] {error_msg}")
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=error_msg
        )


def train_transformer_job(
    job_id: str,
    kmer_content: bytes,
    phenotype_content: bytes,
    model_name: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    k: int,
    job_manager: JobManager
):
    """
    Execute Transformer (DNABERT) training as a background job.
    
    Args:
        job_id: Unique job identifier
        kmer_content: Raw k-mer file content (k=6 for DNABERT)
        phenotype_content: Raw phenotype file content
        model_name: Name for the trained model
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate
        job_manager: JobManager instance for status updates
    """
    try:
        # Update status to running
        job_manager.update_job(
            job_id,
            status=JobStatus.RUNNING,
            progress=0,
            current_step="Starting DNABERT Transformer training pipeline..."
        )
        
        # Import DNABERT modules with error handling
        try:
            from preprocessing.dnabert_processor import DNABERTProcessor
            from models.transformer_trainer import DNABERTTrainer
        except (OSError, ImportError) as e:
            if "DLL" in str(e) or "dll" in str(e).lower():
                error_msg = (
                    f"PyTorch CUDA DLLs failed to load. "
                    f"This is often due to:\n"
                    f"1. CUDA version mismatch\n"
                    f"2. Missing Visual C++ Redistributables\n"
                    f"3. Missing CUDA runtime\n\n"
                    f"Solution: Install CPU-only PyTorch:\n"
                    f"  pip uninstall torch torchvision torchaudio\n"
                    f"  pip install torch torchvision torchaudio\n\n"
                    f"Original error: {str(e)}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                raise
        
        # Step 1: Parse k-mer data and extract gene sequences
        logger.info(f"[{job_id}] Parsing k-mer data for gene extraction with k={k}...")
        job_manager.update_job(
            job_id,
            progress=5,
            current_step=f"Extracting gene sequences from k-mer data (k={k})..."
        )
        
        processor = DNABERTProcessor(k=k, max_length=512)
        genome_to_genes = processor.parse_gene_sequences_from_kmer(kmer_content)
        
        # Step 2: Parse phenotype data
        logger.info(f"[{job_id}] Parsing phenotype data...")
        job_manager.update_job(
            job_id,
            progress=15,
            current_step="Parsing phenotype data..."
        )
        
        from preprocessing.phenotype_parser import PhenotypeParser
        phenotype_parser = PhenotypeParser()
        phenotype_df = phenotype_parser.parse_phenotype_file(phenotype_content)
        
        # Step 3: Create gene-level dataset
        logger.info(f"[{job_id}] Creating gene-level dataset...")
        job_manager.update_job(
            job_id,
            progress=25,
            current_step="Creating gene-level dataset for DNABERT..."
        )
        
        gene_df = processor.create_gene_dataset(genome_to_genes, phenotype_df)
        
        if len(gene_df) < 100:
            raise ValueError(f"Insufficient gene data: {len(gene_df)} genes. Need at least 100.")
        
        logger.info(f"[{job_id}] Gene dataset: {len(gene_df)} genes from {gene_df['genome_id'].nunique()} genomes")
        
        # Step 3.5: Store embeddings in Qdrant for similarity search
        # For DNABERT, we need to build feature vectors from k-mer data
        logger.info(f"[{job_id}] Storing genome embeddings in Qdrant...")
        job_manager.update_job(
            job_id,
            progress=27,
            current_step="Storing genome embeddings in vector database..."
        )
        try:
            qdrant_service = QdrantService()
            if qdrant_service.client:
                # Build feature matrix from k-mer data for embeddings
                kmer_processor = KmerProcessor(k=k)
                kmer_df = kmer_processor.parse_kmer_file(kmer_content)
                X, feature_genome_ids, _ = kmer_processor.build_feature_matrix(kmer_df)
                
                # Align with genomes that have phenotype data
                unique_genome_ids = gene_df['genome_id'].unique().tolist()
                genome_id_to_idx = {gid: i for i, gid in enumerate(feature_genome_ids)}
                aligned_indices = [genome_id_to_idx[gid] for gid in unique_genome_ids if gid in genome_id_to_idx]
                aligned_genome_ids = [gid for gid in unique_genome_ids if gid in genome_id_to_idx]
                X_aligned = X[aligned_indices] if aligned_indices else np.array([]).reshape(0, X.shape[1])
                
                if len(X_aligned) > 0:
                    # Generate embeddings from feature vectors
                    embeddings = _generate_embeddings_from_features(X_aligned, target_dim=768)
                    
                    # Prepare metadata for each genome
                    metadata_list = []
                    for genome_id in aligned_genome_ids:
                        # Get resistance profile for this genome
                        genome_phenotypes = phenotype_df[phenotype_df['genome_id'] == genome_id]
                        resistance_profile = {}
                        for _, row in genome_phenotypes.iterrows():
                            antibiotic = row.get('antibiotic', '')
                            phenotype = row.get('phenotype', '')
                            if antibiotic and phenotype:
                                resistance_profile[antibiotic] = phenotype
                        
                        metadata_list.append({
                            'model_name': model_name,
                            'model_type': 'transformer_dnabert',
                            'k': k,
                            'resistance_profile': resistance_profile,
                            'n_genes': len(gene_df[gene_df['genome_id'] == genome_id])
                        })
                    
                    # Batch insert embeddings
                    inserted_count = qdrant_service.batch_insert_embeddings(
                        genome_ids=aligned_genome_ids,
                        embeddings=embeddings,
                        metadata_list=metadata_list
                    )
                    logger.info(f"[{job_id}] ✅ Stored {inserted_count} genome embeddings in Qdrant")
                else:
                    logger.warning(f"[{job_id}] No aligned genomes found for Qdrant storage")
            else:
                logger.warning(f"[{job_id}] ⚠️  Qdrant not available, skipping embedding storage")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store embeddings in Qdrant (non-critical): {e}")
            # Continue training even if Qdrant fails
        
        # Step 4: Train DNABERT models
        logger.info(f"[{job_id}] Training DNABERT models...")
        job_manager.update_job(
            job_id,
            progress=30,
            current_step="Training DNABERT models (this may take a while)..."
        )
        
        # Check if job was cancelled before starting training
        job = job_manager.get_job(job_id)
        if job and job.status == JobStatus.CANCELLED:
            logger.info(f"[{job_id}] Training cancelled before model training")
            return
        
        def progress_callback(progress, message):
            # Check for cancellation during training
            job = job_manager.get_job(job_id)
            if job and job.status == JobStatus.CANCELLED:
                raise InterruptedError("Training job was cancelled by user")
            job_manager.update_job(job_id, progress=progress, current_step=message)
        
        logger.info(f"[{job_id}] Initializing DNABERT Transformer trainer with GPU support...")
        trainer = DNABERTTrainer(
            model_name="zhihan1996/DNABERT-6",
            max_length=512,
            batch_size=batch_size,
            epochs=epochs,
            learning_rate=learning_rate
        )
        if trainer.device.type == 'cuda':
            logger.info(f"[{job_id}] ✅ DNABERT Transformer will use GPU for training")
        else:
            logger.warning(f"[{job_id}] ⚠️  DNABERT Transformer will use CPU (GPU not available)")
        
        try:
            metrics = trainer.train_per_antibiotic(
                gene_df,
                progress_callback=progress_callback
            )
        except InterruptedError:
            logger.info(f"[{job_id}] Training cancelled during model training")
            job_manager.update_job(
                job_id,
                status=JobStatus.CANCELLED,
                current_step="Training cancelled by user"
            )
            return
        
        # Step 5: Save models
        logger.info(f"[{job_id}] Saving trained models...")
        job_manager.update_job(
            job_id,
            progress=90,
            current_step="Saving trained DNABERT models..."
        )
        
        model_path = trainer.save_models(settings.model_storage_path, model_name)
        
        # Step 6: Calculate summary metrics
        logger.info(f"[{job_id}] Computing summary metrics...")
        job_manager.update_job(
            job_id,
            progress=95,
            current_step="Computing summary metrics..."
        )
        
        # Aggregate metrics
        successful_models = [k for k, v in metrics.items() if 'error' not in v]
        avg_accuracy = sum(m['accuracy'] for k, m in metrics.items() if 'error' not in m) / max(len(successful_models), 1)
        avg_f1 = sum(m['f1_macro'] for k, m in metrics.items() if 'error' not in m) / max(len(successful_models), 1)
        avg_jaccard = sum(m['jaccard_macro'] for k, m in metrics.items() if 'error' not in m) / max(len(successful_models), 1)
        
        summary_metrics = {
            'model_type': 'transformer_dnabert',
            'model_name': model_name,
            'model_path': model_path,
            'n_genes': len(gene_df),
            'n_genomes': gene_df['genome_id'].nunique(),
            'n_antibiotics': len(trainer.antibiotic_names),
            'n_successful_models': len(successful_models),
            'antibiotics': trainer.antibiotic_names,
            'avg_accuracy': float(avg_accuracy),
            'avg_f1_macro': float(avg_f1),
            'avg_jaccard_macro': float(avg_jaccard),
            'per_antibiotic_metrics': metrics,
            'hyperparameters': {
                'epochs': epochs,
                'batch_size': batch_size,
                'learning_rate': learning_rate,
                'base_model': 'DNABERT-6'
            }
        }
        
        # Complete job
        logger.info(f"[{job_id}] DNABERT training completed successfully!")
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            current_step="DNABERT training completed successfully!",
            metrics=summary_metrics
        )
        
    except Exception as e:
        error_msg = f"DNABERT training failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"[{job_id}] {error_msg}")
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=error_msg
        )


def train_parallel_job(
    parent_job_id: str,
    xgb_job_id: str,
    transformer_job_id: str,
    kmer_content: bytes,
    phenotype_content: bytes,
    xgb_model_name: str,
    transformer_model_name: str,
    xgb_max_depth: int,
    xgb_learning_rate: float,
    xgb_n_estimators: int,
    transformer_epochs: int,
    transformer_batch_size: int,
    transformer_learning_rate: float,
    k: int,
    job_manager: JobManager
):
    """
    Execute XGBoost and Transformer training in parallel using threading.
    
    Both models will train simultaneously using separate threads, which is much
    faster than training them sequentially.
    
    Args:
        parent_job_id: Parent job ID
        xgb_job_id: XGBoost job identifier
        transformer_job_id: Transformer job identifier
        kmer_content: Raw k-mer file content
        phenotype_content: Raw phenotype file content
        xgb_model_name: Name for XGBoost model
        transformer_model_name: Name for Transformer model
        xgb_max_depth: XGBoost max tree depth
        xgb_learning_rate: XGBoost learning rate
        xgb_n_estimators: Number of boosting rounds
        transformer_epochs: Number of training epochs
        transformer_batch_size: Training batch size
        transformer_learning_rate: Transformer learning rate
        k: K-mer size
        job_manager: JobManager instance for status updates
    """
    import threading
    
    try:
        logger.info(f"[{parent_job_id}] Starting parallel training (XGBoost + Transformer)")
        logger.info(f"[{parent_job_id}] Both models will prioritize GPU usage")
        job_manager.update_job(
            parent_job_id,
            status=JobStatus.RUNNING,
            progress=0,
            current_step="Starting parallel training for both XGBoost and Transformer models with GPU acceleration..."
        )
        
        # Create child jobs
        job_manager.create_job(
            job_id=xgb_job_id,
            job_type="xgboost",
            metadata={
                "model_name": xgb_model_name,
                "parent_job_id": parent_job_id,
                "k": k
            }
        )
        
        job_manager.create_job(
            job_id=transformer_job_id,
            job_type="transformer",
            metadata={
                "model_name": transformer_model_name,
                "parent_job_id": parent_job_id,
                "k": k
            }
        )
        
        # Launch both training jobs in separate threads
        xgb_thread = threading.Thread(
            target=train_xgboost_job,
            args=(
                xgb_job_id,
                kmer_content,
                phenotype_content,
                xgb_model_name,
                xgb_max_depth,
                xgb_learning_rate,
                xgb_n_estimators,
                k,
                job_manager
            )
        )
        
        transformer_thread = threading.Thread(
            target=train_transformer_job,
            args=(
                transformer_job_id,
                kmer_content,
                phenotype_content,
                transformer_model_name,
                transformer_epochs,
                transformer_batch_size,
                transformer_learning_rate,
                k,
                job_manager
            )
        )
        
        # Start both threads
        logger.info(f"[{parent_job_id}] Launching XGBoost and Transformer training threads...")
        xgb_thread.start()
        transformer_thread.start()
        
        job_manager.update_job(
            parent_job_id,
            progress=10,
            current_step="Both models are now training in parallel. Check individual job statuses for details."
        )
        
        # Wait for both threads to complete
        logger.info(f"[{parent_job_id}] Waiting for both models to complete training...")
        xgb_thread.join()
        transformer_thread.join()
        
        # Check if both completed successfully
        xgb_job = job_manager.get_job(xgb_job_id)
        transformer_job = job_manager.get_job(transformer_job_id)
        
        if xgb_job.status == JobStatus.COMPLETED and transformer_job.status == JobStatus.COMPLETED:
            logger.info(f"[{parent_job_id}] Both models trained successfully!")
            
            # Aggregate metrics
            summary_metrics = {
                "xgboost": xgb_job.metrics,
                "transformer": transformer_job.metrics,
                "comparison": {
                    "xgboost_avg_accuracy": xgb_job.metrics.get('avg_accuracy', 0),
                    "transformer_avg_accuracy": transformer_job.metrics.get('avg_accuracy', 0),
                    "xgboost_avg_f1": xgb_job.metrics.get('avg_f1_macro', 0),
                    "transformer_avg_f1": transformer_job.metrics.get('avg_f1_macro', 0),
                    "winner": "transformer" if transformer_job.metrics.get('avg_f1_macro', 0) > xgb_job.metrics.get('avg_f1_macro', 0) else "xgboost"
                }
            }
            
            job_manager.update_job(
                parent_job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                current_step="Parallel training completed successfully! Both models are ready.",
                metrics=summary_metrics
            )
        else:
            # At least one failed
            error_messages = []
            if xgb_job.status == JobStatus.FAILED:
                error_messages.append(f"XGBoost: {xgb_job.error}")
            if transformer_job.status == JobStatus.FAILED:
                error_messages.append(f"Transformer: {transformer_job.error}")
            
            error_msg = "One or more models failed:\n" + "\n".join(error_messages)
            logger.error(f"[{parent_job_id}] {error_msg}")
            job_manager.update_job(
                parent_job_id,
                status=JobStatus.FAILED,
                error=error_msg
            )
        
    except Exception as e:
        error_msg = f"Parallel training failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"[{parent_job_id}] {error_msg}")
        job_manager.update_job(
            parent_job_id,
            status=JobStatus.FAILED,
            error=error_msg
        )

