"""
FastAPI Backend for Antibiogram Prediction System
Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import warnings

from api.training_routes import router as training_router

# Suppress noisy FutureWarning from transformers / torch._pytree
warnings.filterwarnings(
    "ignore",
    message="`torch.utils._pytree._register_pytree_node` is deprecated.",
    category=FutureWarning,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backend.log')
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Antibiogram Prediction API",
    description="API for training and predicting antibiotic resistance from genomic data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(training_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Antibiogram Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "training": "/api/training",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Antibiogram Prediction API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
