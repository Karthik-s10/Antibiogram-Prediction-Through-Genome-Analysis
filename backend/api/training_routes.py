"""
Training API endpoints for XGBoost and Transformer models.
Handles file uploads and initiates async training jobs.
"""
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from typing import Optional
import uuid
import logging

from jobs.job_manager import JobManager, JobStatus
from jobs.training_job import train_xgboost_job, train_transformer_job, train_parallel_job
from preprocessing.kmer_processor import KmerProcessor

router = APIRouter()
logger = logging.getLogger(__name__)
job_manager = JobManager()


@router.post("/xgboost")
async def train_xgboost(
    background_tasks: BackgroundTasks,
    kmer_file: UploadFile = File(..., description="K-mer data TSV file"),
    phenotype_file: UploadFile = File(..., description="Phenotype CSV file"),
    model_name: Optional[str] = Form(None),
    max_depth: Optional[int] = Form(6),
    learning_rate: Optional[float] = Form(0.1),
    n_estimators: Optional[int] = Form(100),
    k: Optional[int] = Form(None, description="K-mer size (auto-detect if None)")
):
    """
    Train an XGBoost model for antibiotic resistance prediction.
    
    Args:
        kmer_file: K-mer frequency data (TSV format)
        phenotype_file: Phenotype labels (CSV format)
        model_name: Optional custom model name
        max_depth: XGBoost max tree depth
        learning_rate: XGBoost learning rate
        n_estimators: Number of boosting rounds
    
    Returns:
        job_id: Unique identifier for tracking training progress
    """
    # Validate files are provided (no extension check - accept any file)
    if not kmer_file.filename:
        raise HTTPException(status_code=400, detail="K-mer file is required")
    
    if not phenotype_file.filename:
        raise HTTPException(status_code=400, detail="Phenotype file is required")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Read file contents
    try:
        kmer_content = await kmer_file.read()
        phenotype_content = await phenotype_file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded files: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading files: {str(e)}")
    
    # Auto-detect k if not provided
    if k is None:
        k = KmerProcessor.detect_k_from_file(kmer_content)
        logger.info(f"Auto-detected k={k} for XGBoost training")
    
    # Create job
    job_manager.create_job(
        job_id=job_id,
        job_type="xgboost",
        metadata={
            "kmer_filename": kmer_file.filename,
            "phenotype_filename": phenotype_file.filename,
            "model_name": model_name or f"xgboost_{job_id[:8]}",
            "k": k,
            "hyperparameters": {
                "max_depth": max_depth,
                "learning_rate": learning_rate,
                "n_estimators": n_estimators
            }
        }
    )
    
    # Queue training job
    background_tasks.add_task(
        train_xgboost_job,
        job_id=job_id,
        kmer_content=kmer_content,
        phenotype_content=phenotype_content,
        model_name=model_name or f"xgboost_{job_id[:8]}",
        max_depth=max_depth,
        learning_rate=learning_rate,
        n_estimators=n_estimators,
        k=k,
        job_manager=job_manager
    )
    
    logger.info(f"XGBoost training job queued: {job_id}")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "XGBoost training job created successfully",
        "model_name": model_name or f"xgboost_{job_id[:8]}"
    }


@router.post("/transformer")
async def train_transformer(
    background_tasks: BackgroundTasks,
    kmer_file: UploadFile = File(..., description="K-mer data TSV file"),
    phenotype_file: UploadFile = File(..., description="Phenotype CSV file"),
    model_name: Optional[str] = Form(None),
    epochs: Optional[int] = Form(3),
    batch_size: Optional[int] = Form(16),
    learning_rate: Optional[float] = Form(2e-5),
    k: Optional[int] = Form(None, description="K-mer size (auto-detect if None)")
):
    """
    Train a DNABERT Transformer model for antibiotic resistance prediction.
    
    Args:
        kmer_file: K-mer data with k=6 (TSV format)
        phenotype_file: Phenotype labels (CSV format)
        model_name: Optional custom model name
        epochs: Number of training epochs
        batch_size: Training batch size
        learning_rate: Learning rate for fine-tuning
    
    Returns:
        job_id: Unique identifier for tracking training progress
    """
    # Validate files are provided (no extension check - accept any file)
    if not kmer_file.filename:
        raise HTTPException(status_code=400, detail="K-mer file is required")
    
    if not phenotype_file.filename:
        raise HTTPException(status_code=400, detail="Phenotype file is required")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Read file contents
    try:
        kmer_content = await kmer_file.read()
        phenotype_content = await phenotype_file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded files: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading files: {str(e)}")
    
    # Auto-detect k if not provided
    if k is None:
        k = KmerProcessor.detect_k_from_file(kmer_content)
        logger.info(f"Auto-detected k={k} for Transformer training")
    
    # Create job
    job_manager.create_job(
        job_id=job_id,
        job_type="transformer",
        metadata={
            "kmer_filename": kmer_file.filename,
            "phenotype_filename": phenotype_file.filename,
            "model_name": model_name or f"transformer_{job_id[:8]}",
            "k": k,
            "hyperparameters": {
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate
            }
        }
    )
    
    # Queue training job
    background_tasks.add_task(
        train_transformer_job,
        job_id=job_id,
        kmer_content=kmer_content,
        phenotype_content=phenotype_content,
        model_name=model_name or f"transformer_{job_id[:8]}",
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        k=k,
        job_manager=job_manager
    )
    
    logger.info(f"Transformer training job queued: {job_id}")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Transformer training job created successfully",
        "model_name": model_name or f"transformer_{job_id[:8]}"
    }


@router.post("/parallel")
async def train_parallel(
    background_tasks: BackgroundTasks,
    kmer_file: UploadFile = File(..., description="K-mer data TSV file"),
    phenotype_file: UploadFile = File(..., description="Phenotype CSV file"),
    model_name: Optional[str] = Form(None),
    # XGBoost parameters
    xgb_max_depth: Optional[int] = Form(6),
    xgb_learning_rate: Optional[float] = Form(0.1),
    xgb_n_estimators: Optional[int] = Form(100),
    # Transformer parameters
    transformer_epochs: Optional[int] = Form(3),
    transformer_batch_size: Optional[int] = Form(16),
    transformer_learning_rate: Optional[float] = Form(2e-5),
    # K-mer size
    k: Optional[int] = Form(None, description="K-mer size (auto-detect if None)")
):
    """
    Train both XGBoost and Transformer models in parallel.
    
    This endpoint trains both models simultaneously, which is faster than
    training them sequentially. Both models will use the same k-mer data
    and phenotype labels.
    
    Args:
        kmer_file: K-mer frequency data (TSV format)
        phenotype_file: Phenotype labels (CSV format)
        model_name: Optional base model name (will append _xgboost and _transformer)
        xgb_max_depth: XGBoost max tree depth
        xgb_learning_rate: XGBoost learning rate
        xgb_n_estimators: Number of boosting rounds
        transformer_epochs: Number of training epochs
        transformer_batch_size: Training batch size
        transformer_learning_rate: Transformer learning rate
        k: K-mer size (auto-detect if None)
    
    Returns:
        Two job IDs: one for XGBoost, one for Transformer
    """
    # Validate files are provided (no extension check - accept any file)
    if not kmer_file.filename:
        raise HTTPException(status_code=400, detail="K-mer file is required")
    
    if not phenotype_file.filename:
        raise HTTPException(status_code=400, detail="Phenotype file is required")
    
    # Generate unique job IDs
    parent_job_id = str(uuid.uuid4())
    xgb_job_id = f"{parent_job_id}_xgboost"
    transformer_job_id = f"{parent_job_id}_transformer"
    
    # Read file contents
    try:
        kmer_content = await kmer_file.read()
        phenotype_content = await phenotype_file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded files: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading files: {str(e)}")
    
    # Auto-detect k if not provided
    if k is None:
        k = KmerProcessor.detect_k_from_file(kmer_content)
        logger.info(f"Auto-detected k={k} for parallel training")
    
    # Generate model names
    base_name = model_name or f"parallel_{parent_job_id[:8]}"
    xgb_model_name = f"{base_name}_xgboost"
    transformer_model_name = f"{base_name}_transformer"
    
    # Create parent job
    job_manager.create_job(
        job_id=parent_job_id,
        job_type="parallel",
        metadata={
            "kmer_filename": kmer_file.filename,
            "phenotype_filename": phenotype_file.filename,
            "model_name": base_name,
            "k": k,
            "xgboost_job_id": xgb_job_id,
            "transformer_job_id": transformer_job_id
        }
    )
    
    # Queue parallel training job
    background_tasks.add_task(
        train_parallel_job,
        parent_job_id=parent_job_id,
        xgb_job_id=xgb_job_id,
        transformer_job_id=transformer_job_id,
        kmer_content=kmer_content,
        phenotype_content=phenotype_content,
        xgb_model_name=xgb_model_name,
        transformer_model_name=transformer_model_name,
        xgb_max_depth=xgb_max_depth,
        xgb_learning_rate=xgb_learning_rate,
        xgb_n_estimators=xgb_n_estimators,
        transformer_epochs=transformer_epochs,
        transformer_batch_size=transformer_batch_size,
        transformer_learning_rate=transformer_learning_rate,
        k=k,
        job_manager=job_manager
    )
    
    logger.info(f"Parallel training jobs queued: XGBoost={xgb_job_id}, Transformer={transformer_job_id}")
    
    return {
        "parent_job_id": parent_job_id,
        "xgboost_job_id": xgb_job_id,
        "transformer_job_id": transformer_job_id,
        "status": "queued",
        "message": "Parallel training jobs created successfully. Both models will train simultaneously.",
        "models": {
            "xgboost": xgb_model_name,
            "transformer": transformer_model_name
        }
    }

