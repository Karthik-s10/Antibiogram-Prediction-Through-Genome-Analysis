"""
Training API Routes
Endpoints for initiating and monitoring model training.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import threading
import logging

from jobs.job_manager import JobManager
from jobs.training_job import train_xgboost_job, train_transformer_job, train_parallel_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["training"])

# Global job manager instance
job_manager = JobManager()


class TrainingRequest(BaseModel):
    """Request model for training."""
    phenotype_file: str
    kmer_file: str
    rosetta_file: str = "BVBRC_genome.txt"
    model_type: str = "parallel"  # 'xgboost', 'transformer', or 'parallel'
    xgboost_model_name: Optional[str] = "xgboost_amr_model"
    transformer_model_name: Optional[str] = "dnabert_amr_model"


class JobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    type: str
    status: str
    progress: float
    message: str
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/train", response_model=JobResponse)
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    """
    Start a training job.
    
    This endpoint initiates background training and returns immediately with a job ID.
    Use the /status/{job_id} endpoint to monitor progress.
    
    Args:
        request: Training configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        Job information
    """
    try:
        # Create job
        job_id = job_manager.create_job(
            job_type=request.model_type,
            metadata={
                "phenotype_file": request.phenotype_file,
                "kmer_file": request.kmer_file,
                "rosetta_file": request.rosetta_file
            }
        )
        
        # Start training in background
        if request.model_type == "xgboost":
            thread = threading.Thread(
                target=train_xgboost_job,
                args=(
                    job_id,
                    request.phenotype_file,
                    request.kmer_file,
                    request.rosetta_file,
                    job_manager,
                    request.xgboost_model_name
                )
            )
        elif request.model_type == "transformer":
            thread = threading.Thread(
                target=train_transformer_job,
                args=(
                    job_id,
                    request.phenotype_file,
                    request.kmer_file,
                    request.rosetta_file,
                    job_manager,
                    request.transformer_model_name
                )
            )
        elif request.model_type == "parallel":
            thread = threading.Thread(
                target=train_parallel_job,
                args=(
                    job_id,
                    request.phenotype_file,
                    request.kmer_file,
                    request.rosetta_file,
                    job_manager,
                    request.xgboost_model_name,
                    request.transformer_model_name
                )
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model_type: {request.model_type}. Must be 'xgboost', 'transformer', or 'parallel'"
            )
        
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started training job {job_id} of type {request.model_type}")
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            message=f"Training job started. Use /api/training/status/{job_id} to monitor progress."
        )
        
    except Exception as e:
        logger.error(f"Failed to start training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a training job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Job status information
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return JobStatusResponse(**job)


@router.get("/jobs", response_model=list)
async def list_jobs(job_type: Optional[str] = None):
    """
    List all training jobs.
    
    Args:
        job_type: Optional filter by job type
        
    Returns:
        List of jobs
    """
    jobs = job_manager.list_jobs(job_type=job_type)
    return jobs


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a training job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        Success message
    """
    success = job_manager.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return {"message": f"Job {job_id} deleted successfully"}


@router.post("/cleanup")
async def cleanup_old_jobs(max_age_hours: int = 24):
    """
    Clean up old completed/failed jobs.
    
    Args:
        max_age_hours: Maximum age in hours
        
    Returns:
        Number of jobs deleted
    """
    deleted_count = job_manager.cleanup_old_jobs(max_age_hours=max_age_hours)
    return {"deleted_count": deleted_count, "message": f"Cleaned up {deleted_count} old jobs"}
