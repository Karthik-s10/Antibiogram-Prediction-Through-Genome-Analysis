"""
Training job implementations for XGBoost and Transformer models.
Executes training pipelines as background tasks.
"""
import logging
import traceback
from typing import Optional
import numpy as np
from pathlib import Path
import shutil
import json

from jobs.job_manager import JobManager, JobStatus
from preprocessing.kmer_processor import KmerProcessor
from preprocessing.phenotype_parser import PhenotypeParser
from preprocessing.data_preprocessor import DataPreprocessor
from models.xgboost_trainer import XGBoostTrainer
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService
from config import settings

logger = logging.getLogger(__name__)


def _cleanup_uploaded_files(job_id: str, phenotype_path: Optional[str], kmer_path: Optional[str] = None, rosetta_path: Optional[str] = None) -> None:
    """Remove temporary uploaded_data directories created for this job, if any.

    Only directories under backend/uploaded_data whose name matches this job_id
    are removed; shared/global resources like BVBRC_genome.txt in other
    locations are left untouched.
    """
    try:
        candidate_paths = [p for p in [phenotype_path, kmer_path, rosetta_path] if p]
        if not candidate_paths:
            return

        parent_dirs = {Path(p).parent for p in candidate_paths}
        for parent in parent_dirs:
            if "uploaded_data" in parent.parts and parent.name == job_id:
                shutil.rmtree(parent, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to cleanup uploaded_data files: {e}")


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
    job_manager: JobManager,
    use_rosetta_preprocessor: bool = False,
    phenotype_path: Optional[str] = None,
    kmer_path: Optional[str] = None,
    rosetta_path: Optional[str] = None,
    max_genomes: int = 1000,
    cycle_index: int = 0,
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
        kmer_processor = None
        preprocessor: Optional[DataPreprocessor] = None
        # Update status to running
        job_manager.update_job(
            job_id,
            status=JobStatus.RUNNING,
            progress=0,
            current_step="Starting XGBoost training pipeline..."
        )
        assembly_metadata = {}
        genome_stats = {}
        
        # Step 1: Data preprocessing / alignment
        if use_rosetta_preprocessor and phenotype_path and kmer_path and rosetta_path:
            # Use BV-BRC Rosetta-based preprocessing via DataPreprocessor
            logger.info(f"[{job_id}] Using Rosetta-based DataPreprocessor pipeline")
            job_manager.update_job(
                job_id,
                progress=5,
                current_step="Initializing Rosetta-based data preprocessor...",
            )

            preprocessor = DataPreprocessor(rosetta_file=rosetta_path)

            job_manager.update_job(
                job_id,
                progress=10,
                current_step=(
                    "Running BV-BRC preprocessing (ID mapping + k-mer/phenotype alignment)..."
                ),
            )

            X_df, Y_df, data_summary = preprocessor.preprocess_data(
                phenotype_file=phenotype_path,
                kmer_file=kmer_path,
                use_cache=False,
                save_cache=True,
            )

            job_manager.update_job(
                job_id,
                progress=20,
                current_step=(
                    f"Data aligned (Rosetta): {len(X_df)} genomes, "
                    f"{X_df.shape[1]} features, {Y_df.shape[1]} antibiotics"
                ),
            )

            # Record detailed genome counts from preprocessing
            try:
                genome_stats = {
                    'n_phenotype_records': int(data_summary.get('n_phenotype_records') or 0),
                    'n_kmer_records': int(data_summary.get('n_kmer_records') or 0),
                    'n_phenotype_genomes': int(data_summary.get('n_phenotype_genomes') or 0),
                    'n_kmer_genomes': int(data_summary.get('n_kmer_genomes') or 0),
                    'n_kmer_genomes_after_filter': int(data_summary.get('n_kmer_genomes_after_filter') or 0),
                    'n_aligned_genomes': int(data_summary.get('n_aligned_genomes') or len(X_df)),
                }
            except Exception:
                # Fail silently if anything goes wrong; training should still proceed
                genome_stats = {}

            # Convert to numpy arrays for trainer
            aligned_genome_ids = list(X_df.index)
            feature_names = [str(c) for c in X_df.columns]
            antibiotic_names = [str(c) for c in Y_df.columns]

            X_aligned = X_df.to_numpy(dtype=np.float32)
            Y_values = Y_df.to_numpy()
            # Convert NaN to -1 to match PhenotypeParser semantics
            y = np.where(np.isnan(Y_values), -1, Y_values).astype(np.int8)
        else:
            # Fallback: use in-memory KmerProcessor + PhenotypeParser pipeline
            logger.info(f"[{job_id}] Using in-memory k-mer/phenotype pipeline")
            # Step 1: Parse k-mer data
            logger.info(f"[{job_id}] Parsing k-mer data with k={k}...")
            job_manager.update_job(
                job_id,
                progress=5,
                current_step=f"Parsing k-mer data (k={k})...",
            )

            kmer_processor = KmerProcessor(k=k)
            kmer_df = kmer_processor.parse_kmer_file(kmer_content)

            # Step 2: Build feature matrix
            logger.info(f"[{job_id}] Building feature matrix...")
            job_manager.update_job(
                job_id,
                progress=10,
                current_step="Building feature matrix...",
            )

            X, feature_genome_ids, feature_names = kmer_processor.build_feature_matrix(kmer_df)

            # Step 3: Parse phenotype data
            logger.info(f"[{job_id}] Parsing phenotype data...")
            job_manager.update_job(
                job_id,
                progress=15,
                current_step="Parsing phenotype data...",
            )

            phenotype_parser = PhenotypeParser()
            phenotype_df = phenotype_parser.parse_phenotype_file(phenotype_content)

            # Step 4: Align data
            logger.info(f"[{job_id}] Aligning feature and label data...")
            job_manager.update_job(
                job_id,
                progress=20,
                current_step="Aligning feature and label matrices...",
            )

            aligned_genome_ids, y, antibiotic_names = phenotype_parser.align_data(
                feature_genome_ids,
                phenotype_df,
            )

            # Filter X to only include aligned genomes
            genome_id_to_idx = {gid: i for i, gid in enumerate(feature_genome_ids)}
            aligned_indices = [genome_id_to_idx[gid] for gid in aligned_genome_ids]
            X_aligned = X[aligned_indices]

            # Detailed genome stats for in-memory path
            try:
                n_kmer_genomes = len(feature_genome_ids)
                n_phenotype_genomes = int(phenotype_df['genome_id'].nunique())
                n_aligned_genomes = len(aligned_genome_ids)
                genome_stats = {
                    'n_phenotype_records': int(len(phenotype_df)),
                    'n_kmer_records': int(len(kmer_df)),
                    'n_phenotype_genomes': int(n_phenotype_genomes),
                    'n_kmer_genomes': int(n_kmer_genomes),
                    # No early k-mer filtering step here, so this equals n_kmer_genomes
                    'n_kmer_genomes_after_filter': int(n_kmer_genomes),
                    'n_aligned_genomes': int(n_aligned_genomes),
                }
            except Exception:
                genome_stats = genome_stats or {}
        
        logger.info(
            f"[{job_id}] Training data: {X_aligned.shape[0]} genomes, "
            f"{X_aligned.shape[1]} features, {len(antibiotic_names)} antibiotics",
        )
        
        # Apply max_genomes/cycle_index limit to create deterministic chunks
        original_genome_count = X_aligned.shape[0]
        if max_genomes and original_genome_count > max_genomes:
            start = cycle_index * max_genomes
            end = min(start + max_genomes, original_genome_count)
            if start >= original_genome_count:
                raise ValueError(
                    f"cycle_index {cycle_index} is out of range for {original_genome_count} genomes "
                    f"with max_genomes={max_genomes}"
                )
            logger.info(
                f"[{job_id}] Using genomes [{start}:{end}] out of {original_genome_count} "
                f"(chunk size {max_genomes}, cycle_index={cycle_index})"
            )
            job_manager.update_job(
                job_id,
                progress=21,
                current_step=(
                    f"Training on genomes {start}–{end - 1} out of {original_genome_count} "
                    f"(chunk {cycle_index}, size {max_genomes})"
                ),
            )
            idx = np.arange(start, end)
            X_aligned = X_aligned[idx]
            y = y[idx]
            aligned_genome_ids = [aligned_genome_ids[i] for i in idx]
            logger.info(f"[{job_id}] Chunk contains {len(aligned_genome_ids)} genomes for training")
        
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
                assembly_metadata = {}
                try:
                    if use_rosetta_preprocessor and preprocessor is not None:
                        assembly_metadata = getattr(preprocessor, "assembly_metadata", {}) or {}
                except Exception as e:
                    logger.warning(f"[{job_id}] Failed to load assembly metadata for Qdrant: {e}")
                for genome_idx, genome_id in enumerate(aligned_genome_ids):
                    # Get resistance profile for this genome
                    resistance_profile = {}
                    for i, antibiotic in enumerate(antibiotic_names):
                        label = y[genome_idx, i]
                        if label != -1:  # Only include if label exists
                            resistance_map = {0: 'S', 1: 'I', 2: 'R'}
                            resistance_profile[antibiotic] = resistance_map.get(label, 'Unknown')

                    extra_meta = assembly_metadata.get(genome_id, {}) if assembly_metadata else {}
                    species_name = extra_meta.get('organism_name') or extra_meta.get('genome_name')
                    strain = extra_meta.get('strain')

                    metadata_list.append({
                        'model_name': model_name,
                        'model_type': 'xgboost',
                        'k': k,
                        'resistance_profile': resistance_profile,
                        'n_antibiotics': len(antibiotic_names),
                        'species': species_name,
                        'organism_name': extra_meta.get('organism_name'),
                        'genome_name': extra_meta.get('genome_name'),
                        'strain': strain,
                    })

                # Filter out genomes that already have embeddings stored in Qdrant
                genomes_to_insert = []
                embeddings_to_insert = []
                metadata_to_insert = []
                skipped_existing = 0

                for genome_idx, genome_id in enumerate(aligned_genome_ids):
                    try:
                        if qdrant_service.genome_exists(genome_id):
                            skipped_existing += 1
                            continue
                    except Exception as e:
                        logger.warning(f"[{job_id}] Failed to check existing genome in Qdrant ({genome_id}): {e}")
                        # If existence check fails, fall back to inserting to avoid losing data
                    genomes_to_insert.append(genome_id)
                    embeddings_to_insert.append(embeddings[genome_idx])
                    metadata_to_insert.append(metadata_list[genome_idx])

                if genomes_to_insert:
                    embeddings_array = np.vstack(embeddings_to_insert).astype(np.float32)
                    inserted_count = qdrant_service.batch_insert_embeddings(
                        genome_ids=genomes_to_insert,
                        embeddings=embeddings_array,
                        metadata_list=metadata_to_insert,
                    )
                    logger.info(
                        f"[{job_id}] ✅ Stored {inserted_count} new genome embeddings in Qdrant "
                        f"(skipped {skipped_existing} existing)"
                    )
                else:
                    logger.info(
                        f"[{job_id}] All {len(aligned_genome_ids)} genomes already have embeddings in Qdrant; "
                        f"skipping upsert."
                    )
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

        # Export explainability report with top k-mer features per antibiotic
        try:
            explain_data = {
                "model_type": "xgboost",
                "model_name": model_name,
                "model_path": model_path,
                "n_genomes": int(X_aligned.shape[0]),
                "n_features": int(X_aligned.shape[1]),
                "n_antibiotics": int(len(antibiotic_names)),
                "antibiotics": {},
            }

            for ab_name, ab_metrics in metrics.items():
                if "error" in ab_metrics:
                    continue
                top_features = ab_metrics.get("top_features", [])
                explain_data["antibiotics"][ab_name] = {
                    "top_features": top_features,
                }

            explain_path = Path(model_path).with_name(
                Path(model_path).stem + "_explainability.json"
            )
            with open(explain_path, "w") as f:
                json.dump(explain_data, f, indent=2)
            logger.info(f"[{job_id}] Saved XGBoost explainability report to {explain_path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to save XGBoost explainability report: {e}")
        
        # Save feature info
        if kmer_processor is not None:
            feature_info_path = f"{settings.model_storage_path}/{model_name}_features.json"
            kmer_processor.save_feature_info(feature_info_path)
        else:
            logger.info(f"[{job_id}] Skipping feature info save (no k-mer processor available)")
        
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
        
        # Capture chunking details so the UI can show exactly how many genomes were used
        # versus how many were available after alignment.
        chunking_applied = bool(max_genomes and original_genome_count > max_genomes)

        # High-level genome accounting so the UI can show where genomes are lost
        n_phenotype_records = genome_stats.get('n_phenotype_records') if genome_stats else None
        n_kmer_records = genome_stats.get('n_kmer_records') if genome_stats else None
        n_phenotype_genomes = genome_stats.get('n_phenotype_genomes') if genome_stats else None
        n_kmer_genomes = genome_stats.get('n_kmer_genomes') if genome_stats else None
        n_kmer_genomes_after_filter = genome_stats.get('n_kmer_genomes_after_filter') if genome_stats else None
        n_aligned_genomes = genome_stats.get('n_aligned_genomes') if genome_stats else None

        summary_metrics = {
            'model_type': 'xgboost',
            'model_name': model_name,
            'model_path': model_path,
            # Genomes after alignment and after any chunking
            'n_genomes': X_aligned.shape[0],
            'original_n_genomes': int(original_genome_count),
            'chunking_applied': chunking_applied,
            'max_genomes': max_genomes,
            'cycle_index': cycle_index,
            # Detailed genome flow diagnostics (may be None if not available)
            'n_phenotype_records': n_phenotype_records,
            'n_kmer_records': n_kmer_records,
            'n_phenotype_genomes': n_phenotype_genomes,
            'n_kmer_genomes': n_kmer_genomes,
            'n_kmer_genomes_after_filter': n_kmer_genomes_after_filter,
            'n_aligned_genomes': n_aligned_genomes,
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
    finally:
        _cleanup_uploaded_files(job_id, phenotype_path, kmer_path, rosetta_path)


def train_transformer_job(
    job_id: str,
    kmer_content: bytes,
    phenotype_content: bytes,
    model_name: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    k: int,
    job_manager: JobManager,
    use_rosetta_preprocessor: bool = False,
    phenotype_path: Optional[str] = None,
    rosetta_path: Optional[str] = None,
    max_genomes: int = 1000,
    cycle_index: int = 0,
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
        genome_stats = {}
        
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
        
        # Step 2: Parse phenotype data, optionally using Rosetta-based ID mapping
        logger.info(f"[{job_id}] Parsing phenotype data...")
        job_manager.update_job(
            job_id,
            progress=15,
            current_step="Parsing phenotype data..."
        )

        if use_rosetta_preprocessor and phenotype_path and rosetta_path:
            logger.info(f"[{job_id}] Using Rosetta-based DataPreprocessor for phenotype ID mapping")
            job_manager.update_job(
                job_id,
                progress=18,
                current_step="Mapping phenotype Genome IDs to GenBank Accessions via Rosetta file...",
            )

            preprocessor = DataPreprocessor(rosetta_file=rosetta_path)
            id_mapping = preprocessor.load_id_mapping()
            mapped_pheno_df = preprocessor.load_and_map_phenotypes(phenotype_path, id_mapping)

            # Build phenotype DataFrame compatible with DNABERTProcessor.create_gene_dataset,
            # using Assembly Accession (GenBank) as genome_id to match k-mer genomes.
            phenotype_df = mapped_pheno_df[["Assembly Accession", "Antibiotic", "Resistant Phenotype"]].copy()
            try:
                assembly_metadata = getattr(preprocessor, "assembly_metadata", {}) or {}
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to load assembly metadata for Transformer Qdrant storage: {e}")
            phenotype_df = phenotype_df.rename(
                columns={
                    "Assembly Accession": "genome_id",
                    "Antibiotic": "antibiotic",
                    "Resistant Phenotype": "phenotype",
                }
            )
        else:
            from preprocessing.phenotype_parser import PhenotypeParser
            phenotype_parser = PhenotypeParser()
            phenotype_df = phenotype_parser.parse_phenotype_file(phenotype_content)

        # Optional early chunking: limit DNABERT preprocessing to a subset of aligned genomes
        # so max_genomes/cycle_index also reduce the cost of gene dataset creation.
        if max_genomes:
            try:
                kmer_genome_ids = sorted(genome_to_genes.keys())
                pheno_genome_ids = set(phenotype_df['genome_id'].unique().tolist())
                aligned_genome_ids = [g for g in kmer_genome_ids if g in pheno_genome_ids]
                total_aligned = len(aligned_genome_ids)
                if total_aligned == 0:
                    logger.warning(
                        f"[{job_id}] No overlapping genomes between k-mer and phenotype data for DNABERT preprocessing"
                    )
                elif total_aligned > max_genomes:
                    start = cycle_index * max_genomes
                    end = min(start + max_genomes, total_aligned)
                    if start >= total_aligned:
                        raise ValueError(
                            f"cycle_index {cycle_index} is out of range for {total_aligned} aligned genomes "
                            f"with max_genomes={max_genomes}"
                        )
                    selected_ids = set(aligned_genome_ids[start:end])
                    genome_to_genes = {gid: genes for gid, genes in genome_to_genes.items() if gid in selected_ids}
                    logger.info(
                        f"[{job_id}] Limiting DNABERT preprocessing to genomes {start}-{end - 1} out of {total_aligned} "
                        f"(chunk size {max_genomes}, cycle_index={cycle_index}); "
                        f"{len(genome_to_genes)} genomes retained"
                    )
                    job_manager.update_job(
                        job_id,
                        progress=24,
                        current_step=(
                            f"Preparing DNABERT chunk: genomes {start}\u2013{end - 1} out of {total_aligned} "
                            f"(chunk {cycle_index}, size {max_genomes})"
                        ),
                    )
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to apply early max_genomes chunking for DNABERT: {e}")
        
        # Step 3: Create gene-level dataset
        logger.info(f"[{job_id}] Creating gene-level dataset...")
        job_manager.update_job(
            job_id,
            progress=25,
            current_step="Creating gene-level dataset for DNABERT..."
        )
        
        gene_df = processor.create_gene_dataset(genome_to_genes, phenotype_df)

        # High-level genome accounting for Transformer pipeline
        try:
            n_phenotype_records = int(len(phenotype_df))
            n_phenotype_genomes = int(phenotype_df['genome_id'].nunique())
            n_kmer_genomes = int(len(genome_to_genes))
            # For DNABERT, k-mer genomes and "after filter" are effectively the same
            n_kmer_genomes_after_filter = n_kmer_genomes
            # Aligned genomes before any chunking come from the gene_df
            n_aligned_genomes = int(gene_df['genome_id'].nunique())

            genome_stats = {
                'n_phenotype_records': n_phenotype_records,
                'n_kmer_records': None,
                'n_phenotype_genomes': n_phenotype_genomes,
                'n_kmer_genomes': n_kmer_genomes,
                'n_kmer_genomes_after_filter': n_kmer_genomes_after_filter,
                'n_aligned_genomes': n_aligned_genomes,
            }
        except Exception:
            genome_stats = genome_stats or {}
        
        if len(gene_df) < 100:
            raise ValueError(f"Insufficient gene data: {len(gene_df)} genes. Need at least 100.")
        
        original_genome_count = gene_df['genome_id'].nunique()
        logger.info(f"[{job_id}] Gene dataset: {len(gene_df)} genes from {original_genome_count} genomes")
        
        # Apply max_genomes/cycle_index limit to create deterministic chunks
        if max_genomes and original_genome_count > max_genomes:
            unique_genome_ids = sorted(gene_df['genome_id'].unique().tolist())
            total = len(unique_genome_ids)
            start = cycle_index * max_genomes
            end = min(start + max_genomes, total)
            if start >= total:
                raise ValueError(
                    f"cycle_index {cycle_index} is out of range for {total} genomes "
                    f"with max_genomes={max_genomes}"
                )
            logger.info(
                f"[{job_id}] Using genome IDs [{start}:{end}] out of {total} "
                f"(chunk size {max_genomes}, cycle_index={cycle_index})"
            )
            job_manager.update_job(
                job_id,
                progress=26,
                current_step=(
                    f"Training on genomes {start}–{end - 1} out of {total} "
                    f"(chunk {cycle_index}, size {max_genomes})"
                ),
            )
            selected_ids = set(unique_genome_ids[start:end])
            gene_df = gene_df[gene_df['genome_id'].isin(selected_ids)]
            logger.info(
                f"[{job_id}] Chunk contains {gene_df['genome_id'].nunique()} genomes "
                f"({len(gene_df)} genes) for training"
            )
        
        # Step 3.5: Store embeddings in Qdrant for similarity search
        # For DNABERT, we generate 768-dim embeddings directly from genome DNA sequences
        logger.info(f"[{job_id}] Storing genome embeddings in Qdrant...")
        job_manager.update_job(
            job_id,
            progress=27,
            current_step="Storing genome embeddings in vector database..."
        )
        try:
            qdrant_service = QdrantService()
            if qdrant_service.client:
                # Use DNABERT-based embedding service on CPU to avoid GPU contention
                embedding_service = EmbeddingService(device="cpu")

                # Align with genomes that have phenotype data (using same genome_id convention as gene_df)
                unique_genome_ids = gene_df['genome_id'].unique().tolist()

                aligned_genome_ids = []
                full_sequences = []
                metadata_list = []

                # Build full genome sequences and metadata first
                for genome_id in unique_genome_ids:
                    genes_for_genome = genome_to_genes.get(genome_id)
                    if not genes_for_genome:
                        continue

                    # Reconstruct a representative genome sequence from its genes
                    full_sequence = ''.join(genes_for_genome)

                    aligned_genome_ids.append(genome_id)
                    full_sequences.append(full_sequence)

                    # Build resistance profile metadata for this genome
                    genome_phenotypes = phenotype_df[phenotype_df['genome_id'] == genome_id]
                    resistance_profile = {}
                    for _, row in genome_phenotypes.iterrows():
                        antibiotic = row.get('antibiotic', '')
                        phenotype = row.get('phenotype', '')
                        if antibiotic and phenotype:
                            resistance_profile[antibiotic] = phenotype

                    extra_meta = assembly_metadata.get(genome_id, {}) if assembly_metadata else {}
                    species_name = extra_meta.get('organism_name') or extra_meta.get('genome_name')
                    strain = extra_meta.get('strain')

                    metadata_list.append({
                        'model_name': model_name,
                        'model_type': 'transformer_dnabert',
                        'k': k,
                        'resistance_profile': resistance_profile,
                        'n_genes': len(gene_df[gene_df['genome_id'] == genome_id]),
                        'species': species_name,
                        'organism_name': extra_meta.get('organism_name'),
                        'genome_name': extra_meta.get('genome_name'),
                        'strain': strain,
                    })

                if aligned_genome_ids:
                    # Batch-embed all genome sequences for this chunk on CPU using DNABERT
                    embeddings_list = embedding_service.embed_sequences(full_sequences, batch_size=8)
                    embeddings = [np.array(vec, dtype=np.float32) for vec in embeddings_list]
                    # Filter out genomes that already have embeddings stored in Qdrant
                    genomes_to_insert = []
                    embeddings_to_insert = []
                    metadata_to_insert = []
                    skipped_existing = 0

                    for idx, genome_id in enumerate(aligned_genome_ids):
                        try:
                            if qdrant_service.genome_exists(genome_id):
                                skipped_existing += 1
                                continue
                        except Exception as e:
                            logger.warning(f"[{job_id}] Failed to check existing genome in Qdrant ({genome_id}): {e}")
                            # If existence check fails, fall back to inserting to avoid losing data
                        genomes_to_insert.append(genome_id)
                        embeddings_to_insert.append(embeddings[idx])
                        metadata_to_insert.append(metadata_list[idx])

                    if genomes_to_insert:
                        embeddings_array = np.vstack(embeddings_to_insert).astype(np.float32)
                        inserted_count = qdrant_service.batch_insert_embeddings(
                            genome_ids=genomes_to_insert,
                            embeddings=embeddings_array,
                            metadata_list=metadata_to_insert,
                        )
                        logger.info(
                            f"[{job_id}] ✅ Stored {inserted_count} new genome embeddings in Qdrant "
                            f"(skipped {skipped_existing} existing)"
                        )
                    else:
                        logger.info(
                            f"[{job_id}] All {len(aligned_genome_ids)} genomes already have embeddings in Qdrant; "
                            f"skipping upsert."
                        )
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

        # Use DNABERT v1 6-mer backbone for training.
        # We still parse the k-mer TSV with its original k (e.g., 10) to reconstruct genes,
        # but tokenization for the Transformer always uses 6-mers.
        base_model = "zhihan1996/DNA_bert_6"
        token_k = 6

        trainer = DNABERTTrainer(
            model_name=base_model,
            max_length=512,
            batch_size=batch_size,
            epochs=epochs,
            learning_rate=learning_rate,
            kmer_size=token_k,
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

        # Chunking details for Transformer too
        transformer_original_genomes = int(original_genome_count)
        transformer_chunking_applied = bool(max_genomes and transformer_original_genomes > max_genomes)
        used_genomes = int(gene_df['genome_id'].nunique())

        # Reuse genome_stats for UI diagnostics
        n_phenotype_records = genome_stats.get('n_phenotype_records') if genome_stats else None
        n_kmer_records = genome_stats.get('n_kmer_records') if genome_stats else None
        n_phenotype_genomes = genome_stats.get('n_phenotype_genomes') if genome_stats else None
        n_kmer_genomes = genome_stats.get('n_kmer_genomes') if genome_stats else None
        n_kmer_genomes_after_filter = genome_stats.get('n_kmer_genomes_after_filter') if genome_stats else None
        n_aligned_genomes = genome_stats.get('n_aligned_genomes') if genome_stats else None

        summary_metrics = {
            'model_type': 'transformer_dnabert',
            'model_name': model_name,
            'model_path': model_path,
            'n_genes': len(gene_df),
            'n_genomes': used_genomes,
            'original_n_genomes': transformer_original_genomes,
            'chunking_applied': transformer_chunking_applied,
            'max_genomes': max_genomes,
            'cycle_index': cycle_index,
            # Detailed genome flow diagnostics (may be None if not available)
            'n_phenotype_records': n_phenotype_records,
            'n_kmer_records': n_kmer_records,
            'n_phenotype_genomes': n_phenotype_genomes,
            'n_kmer_genomes': n_kmer_genomes,
            'n_kmer_genomes_after_filter': n_kmer_genomes_after_filter,
            'n_aligned_genomes': n_aligned_genomes,
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
                'base_model': base_model,
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
    finally:
        _cleanup_uploaded_files(job_id, phenotype_path, None, rosetta_path)


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
    job_manager: JobManager,
    use_rosetta_preprocessor: bool = False,
    phenotype_path: Optional[str] = None,
    kmer_path: Optional[str] = None,
    rosetta_path: Optional[str] = None,
    max_genomes: int = 1000,
    cycle_index: int = 0,
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
                "k": k,
                "use_rosetta_preprocessor": bool(use_rosetta_preprocessor),
            },
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
                job_manager,
                use_rosetta_preprocessor,
                phenotype_path,
                kmer_path,
                rosetta_path,
                max_genomes,
                cycle_index,
            ),
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
                job_manager,
                use_rosetta_preprocessor,
                phenotype_path,
                rosetta_path,
                max_genomes,
                cycle_index,
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
    finally:
        # Clean up parent-level uploaded_data directory (files were stored under parent_job_id)
        _cleanup_uploaded_files(parent_job_id, phenotype_path, kmer_path, rosetta_path)

