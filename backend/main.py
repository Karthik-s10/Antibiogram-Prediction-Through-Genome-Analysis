"""
FastAPI main application for Antibiotic Resistance Prediction ML Pipeline.
Provides endpoints for model training, prediction, and status monitoring.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import warnings

# Suppress noisy FutureWarning from transformers / torch._pytree
warnings.filterwarnings(
    "ignore",
    message="`torch.utils._pytree._register_pytree_node` is deprecated.",
    category=FutureWarning,
)

from config import settings
from api import training_routes, prediction_routes, status_routes
from models.xgboost_trainer import XGBoostTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting ML Pipeline API...")
    logger.info(f"Model storage path: {settings.model_storage_path}")
    logger.info(f"Frontend URL: {settings.frontend_url}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ML Pipeline API...")


# Initialize FastAPI app
app = FastAPI(
    title="Antibiotic Resistance Prediction API",
    description="ML Pipeline for training and predicting bacterial antibiotic resistance",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - Allow all localhost ports for development
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",  # Allow any localhost port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(training_routes.router, prefix="/api/train", tags=["Training"])
app.include_router(prediction_routes.router, prefix="/api/predict", tags=["Prediction"])
app.include_router(status_routes.router, prefix="/api/status", tags=["Status"])


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Antibiotic Resistance Prediction API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_storage": settings.model_storage_path
    }


@app.get("/api/gpu/status")
async def gpu_status():
    """
    Get GPU status and availability information.
    Returns detailed information about GPU availability for training.
    """
    gpu_info = {
        "gpu_available": False,
        "gpu_type": None,
        "gpu_name": None,
        "xgb_gpu_support": False,
        "device_detected": "cpu",
        "details": {}
    }
    
    # Use XGBoostTrainer's GPU detection
    trainer = XGBoostTrainer(use_gpu=True)
    gpu_info["device_detected"] = trainer.device
    
    # Detailed GPU detection
    gpu_detected = False
    gpu_name = None
    gpu_type = None
    
    # Try PyTorch first (supports NVIDIA CUDA, AMD ROCm, Intel, Apple MPS)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_detected = True
            gpu_name = torch.cuda.get_device_name(0)
            gpu_type = "NVIDIA CUDA"
            gpu_info["details"]["cuda_version"] = torch.version.cuda
            gpu_info["details"]["cudnn_version"] = torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
            gpu_info["details"]["gpu_memory_mb"] = torch.cuda.get_device_properties(0).total_memory / (1024**2)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            gpu_detected = True
            gpu_name = "Apple Silicon GPU"
            gpu_type = "Apple Metal"
            gpu_info["details"]["note"] = "XGBoost doesn't support MPS yet, will use CPU"
    except ImportError:
        pass
    
    # Try NVIDIA via nvidia-smi
    if not gpu_detected:
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                gpu_detected = True
                gpu_type = "NVIDIA"
                # Parse nvidia-smi output for GPU name
                for line in result.stdout.split('\n'):
                    if 'NVIDIA' in line or 'GeForce' in line or 'Tesla' in line or 'Quadro' in line:
                        gpu_name = line.strip()
                        break
                if not gpu_name:
                    gpu_name = "NVIDIA GPU (detected via nvidia-smi)"
                gpu_info["details"]["nvidia_smi_output"] = result.stdout[:500]  # First 500 chars
        except Exception as e:
            pass
    
    # Try AMD ROCm
    if not gpu_detected:
        try:
            import subprocess
            result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                gpu_detected = True
                gpu_type = "AMD"
                gpu_name = "AMD GPU (ROCm)"
                gpu_info["details"]["rocm_available"] = True
        except Exception:
            pass
    
    # Try Intel GPU via Windows wmic
    if not gpu_detected:
        try:
            import subprocess
            import platform
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    output = result.stdout.lower()
                    if any(gpu in output for gpu in ['nvidia', 'geforce', 'quadro', 'tesla']):
                        gpu_detected = True
                        gpu_type = "NVIDIA"
                        gpu_name = "NVIDIA GPU (Windows detection)"
                    elif any(gpu in output for gpu in ['amd', 'radeon', 'rx']):
                        gpu_detected = True
                        gpu_type = "AMD"
                        gpu_name = "AMD GPU (Windows detection)"
                    elif any(gpu in output for gpu in ['intel', 'arc']) and 'arc' in output:
                        gpu_detected = True
                        gpu_type = "Intel Arc"
                        gpu_name = "Intel Arc GPU (Windows detection)"
                        gpu_info["details"]["note"] = "Intel Arc support is experimental"
        except Exception:
            pass
    
    gpu_info["gpu_available"] = gpu_detected
    gpu_info["gpu_type"] = gpu_type
    gpu_info["gpu_name"] = gpu_name
    
    # Check if XGBoost will actually use GPU
    if trainer.device == 'cuda':
        gpu_info["xgb_gpu_support"] = True
        gpu_info["details"]["xgb_tree_method"] = "gpu_hist"
        gpu_info["details"]["xgb_predictor"] = "gpu_predictor"
    else:
        gpu_info["xgb_gpu_support"] = False
        gpu_info["details"]["xgb_tree_method"] = "hist (CPU)"
        gpu_info["details"]["xgb_note"] = "XGBoost will use CPU. GPU may not be properly configured for XGBoost."
    
    # Check Transformer (DNABERT) GPU support
    try:
        from models.transformer_trainer import DNABERTTrainer
        transformer_trainer = DNABERTTrainer()
        gpu_info["transformer_gpu_support"] = transformer_trainer.device.type == 'cuda'
        if transformer_trainer.device.type == 'cuda':
            gpu_info["details"]["transformer_device"] = "cuda (GPU)"
            gpu_info["details"]["transformer_fp16"] = True
        else:
            gpu_info["details"]["transformer_device"] = "cpu"
            gpu_info["details"]["transformer_fp16"] = False
            gpu_info["details"]["transformer_note"] = "DNABERT will use CPU. Install PyTorch with CUDA support for GPU acceleration."
    except Exception as e:
        gpu_info["transformer_gpu_support"] = False
        gpu_info["details"]["transformer_error"] = str(e)
    
    # Summary
    if gpu_info["xgb_gpu_support"] and gpu_info.get("transformer_gpu_support", False):
        gpu_info["details"]["parallel_training"] = "Both XGBoost and Transformer will use GPU simultaneously"
    elif gpu_info["xgb_gpu_support"] or gpu_info.get("transformer_gpu_support", False):
        gpu_info["details"]["parallel_training"] = "Only one model will use GPU (the other will use CPU)"
    else:
        gpu_info["details"]["parallel_training"] = "Both models will use CPU (GPU not available)"
    
    return gpu_info


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

