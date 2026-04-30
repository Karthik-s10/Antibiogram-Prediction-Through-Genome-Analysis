"""
API endpoints for model explainability using SHAP.
Provides endpoints for generating and retrieving model explanations.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks  # type: ignore
from pydantic import BaseModel, Field  # type: ignore
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

from explainability import SHAPUtils, XGBoostExplainer, TransformerExplainer  # type: ignore
from models.xgboost_trainer import XGBoostTrainer  # type: ignore
from models.transformer_trainer import DNABERTTrainer  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/explanations", tags=["explanations"])

# Initialize explainers
xgboost_explainer = None
transformer_explainer = None
shap_utils = SHAPUtils()

# Request models
class ExplanationRequest(BaseModel):
    antibiotic: str = Field(..., description="Antibiotic name")
    model_type: str = Field(..., description="Model type: 'xgboost' or 'transformer'")
    features: Optional[List[float]] = Field(None, description="Feature vector for XGBoost models")
    sequence: Optional[str] = Field(None, description="DNA sequence for transformer models")
    prediction: Optional[str] = Field(None, description="Model prediction (S/I/R)")
    probability: Optional[float] = Field(None, description="Prediction probability")

class BatchExplanationRequest(BaseModel):
    antibiotic: str = Field(..., description="Antibiotic name")
    model_type: str = Field(..., description="Model type: 'xgboost' or 'transformer'")
    features_batch: Optional[List[List[float]]] = Field(None, description="Batch of feature vectors")
    sequences: Optional[List[str]] = Field(None, description="Batch of DNA sequences")
    predictions: Optional[List[str]] = Field(None, description="Batch of predictions")
    probabilities: Optional[List[float]] = Field(None, description="Batch of probabilities")

class GlobalImportanceRequest(BaseModel):
    antibiotic: str = Field(..., description="Antibiotic name")
    model_type: str = Field(..., description="Model type: 'xgboost' or 'transformer'")
    background_samples: Optional[List[List[float]]] = Field(None, description="Background samples for SHAP")
    n_samples: int = Field(100, description="Number of samples for background")

class SummaryRequest(BaseModel):
    antibiotics: List[str] = Field(..., description="List of antibiotic names")
    model_type: str = Field(..., description="Model type: 'xgboost' or 'transformer'")

# Response models
class ExplanationResponse(BaseModel):
    success: bool
    explanation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class BatchExplanationResponse(BaseModel):
    success: bool
    explanations: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

def initialize_explainers():
    """Initialize explainers (call this during app startup)."""
    global xgboost_explainer, transformer_explainer
    
    try:
        xgboost_explainer = XGBoostExplainer()
        logger.info("XGBoost explainer initialized")
    except Exception as e:
        logger.error(f"Failed to initialize XGBoost explainer: {str(e)}")
    
    try:
        import os
        from config import settings  # type: ignore
        models_dir = settings.model_storage_path
        transformer_explainer = TransformerExplainer(models_dir=models_dir)
        logger.info(f"Transformer explainer initialized (models_dir={models_dir})")
    except Exception as e:
        logger.error(f"Failed to initialize Transformer explainer: {str(e)}")

@router.post("/single", response_model=ExplanationResponse)
async def explain_single_sample(request: ExplanationRequest):
    """
    Generate SHAP explanation for a single sample.
    
    Supports both XGBoost (k-mer features) and DNABERT (DNA sequence) models.
    """
    start_time = datetime.now()
    
    try:
        # Validate request
        if request.model_type.lower() == "xgboost":
            if xgboost_explainer is None:
                raise HTTPException(status_code=500, detail="XGBoost explainer not initialized")

            if request.features is None and request.sequence is not None:
                from preprocessing.kmer_processor import KmerProcessor  # type: ignore
                from config import settings  # type: ignore
                k_size = getattr(settings, 'kmer_size_xgboost', 10)
                processor = KmerProcessor(k=k_size)
                fasta_content = f">SEQ\\n{request.sequence}"
                kmer_counts = processor.extract_kmers_from_fasta(fasta_content)
                
                feature_names = xgboost_explainer.get_feature_names(request.antibiotic)
                if feature_names:
                    request.features = [float(kmer_counts.get(feat, 0)) for feat in feature_names]

            if request.features is None:
                raise HTTPException(status_code=400, detail="Features required for XGBoost models")
            
            # Generate explanation
            explanation = xgboost_explainer.explain_single_sample(
                antibiotic=request.antibiotic,
                features=request.features,
                prediction=request.prediction,
                probability=request.probability
            )
            
        elif request.model_type.lower() == "transformer":
            if request.sequence is None:
                raise HTTPException(status_code=400, detail="Sequence required for transformer models")
            
            if transformer_explainer is None:
                raise HTTPException(status_code=500, detail="Transformer explainer not initialized")
            
            # Generate explanation
            explanation = transformer_explainer.explain_single_sample(
                antibiotic=request.antibiotic,
                sequence=request.sequence,
                prediction=request.prediction,
                probability=request.probability
            )
            
        else:
            raise HTTPException(status_code=400, detail="Invalid model type. Use 'xgboost' or 'transformer'")
        
        # Format for frontend
        formatted_explanation = shap_utils.format_explanation_for_frontend(explanation)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ExplanationResponse(  # type: ignore
            success=True,
            explanation=formatted_explanation,  # type: ignore
            processing_time=processing_time  # type: ignore
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in single sample explanation: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ExplanationResponse(  # type: ignore
            success=False,
            error=str(e),  # type: ignore
            processing_time=processing_time  # type: ignore
        )

@router.post("/batch", response_model=BatchExplanationResponse)
async def explain_batch_samples(request: BatchExplanationRequest):
    """
    Generate SHAP explanations for a batch of samples.
    
    More efficient than multiple single requests for large batches.
    """
    start_time = datetime.now()
    
    try:
        # Validate request
        if request.model_type.lower() == "xgboost":
            if request.features_batch is None:
                raise HTTPException(status_code=400, detail="Features batch required for XGBoost models")
            
            if xgboost_explainer is None:
                raise HTTPException(status_code=500, detail="XGBoost explainer not initialized")
            
            # Generate batch explanations
            explanations = xgboost_explainer.explain_batch(
                antibiotic=request.antibiotic,
                features_batch=request.features_batch,
                predictions=request.predictions,
                probabilities=request.probabilities
            )
            
        elif request.model_type.lower() == "transformer":
            if request.sequences is None:
                raise HTTPException(status_code=400, detail="Sequences required for transformer models")
            
            if transformer_explainer is None:
                raise HTTPException(status_code=500, detail="Transformer explainer not initialized")
            
            # Generate batch explanations
            explanations = transformer_explainer.explain_batch(
                antibiotic=request.antibiotic,
                sequences=request.sequences,
                predictions=request.predictions,
                probabilities=request.probabilities
            )
            
        else:
            raise HTTPException(status_code=400, detail="Invalid model type. Use 'xgboost' or 'transformer'")
        
        # Format explanations for frontend
        formatted_explanations = [
            shap_utils.format_explanation_for_frontend(exp) for exp in explanations
        ]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BatchExplanationResponse(  # type: ignore
            success=True,
            explanations=formatted_explanations,  # type: ignore
            processing_time=processing_time  # type: ignore
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch explanation: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BatchExplanationResponse(  # type: ignore
            success=False,
            error=str(e),  # type: ignore
            processing_time=processing_time  # type: ignore
        )

@router.post("/global-importance", response_model=ExplanationResponse)
async def get_global_feature_importance(request: GlobalImportanceRequest):
    """
    Get global feature importance for a specific antibiotic model.
    
    Returns overall feature importance across the model's feature space.
    """
    start_time = datetime.now()
    
    try:
        if request.model_type.lower() == "xgboost":
            if xgboost_explainer is None:
                raise HTTPException(status_code=500, detail="XGBoost explainer not initialized")
            
            # Get global importance
            importance = xgboost_explainer.get_global_feature_importance(
                antibiotic=request.antibiotic,
                background_samples=request.background_samples,
                n_samples=request.n_samples
            )
            
            explanation_data = {
                'type': 'global_importance',
                'antibiotic': request.antibiotic,
                'model_type': 'XGBoost',
                'feature_importance': importance,
                'total_features': len(importance),
                'background_samples': request.n_samples
            }
            
        elif request.model_type.lower() == "transformer":
            if transformer_explainer is None:
                raise HTTPException(status_code=500, detail="Transformer explainer not initialized")
            
            # For transformers, use token importance summary
            sample_sequences = [
                "ATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTA",
                "CCCCGGGGAAAATTTT"
            ]
            
            token_summary = transformer_explainer.get_token_importance_summary(
                antibiotic=request.antibiotic,
                sequences=sample_sequences,
                top_k=100
            )
            
            explanation_data = {
                'type': 'token_importance',
                'antibiotic': request.antibiotic,
                'model_type': 'DNABERT',
                'token_importance': token_summary,
                'sample_sequences': len(sample_sequences)
            }
            
        else:
            raise HTTPException(status_code=400, detail="Invalid model type. Use 'xgboost' or 'transformer'")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ExplanationResponse(  # type: ignore
            success=True,
            explanation=explanation_data,  # type: ignore
            processing_time=processing_time  # type: ignore
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting global importance: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ExplanationResponse(  # type: ignore
            success=False,
            error=str(e),  # type: ignore
            processing_time=processing_time  # type: ignore
        )

@router.post("/summary", response_model=ExplanationResponse)
async def get_explanation_summary(request: SummaryRequest):
    """
    Get a summary of explanations for multiple antibiotics.
    
    Provides cross-antibiotic analysis of feature/token importance patterns.
    """
    start_time = datetime.now()
    
    try:
        if request.model_type.lower() == "xgboost":
            if xgboost_explainer is None:
                raise HTTPException(status_code=500, detail="XGBoost explainer not initialized")
            
            # Get XGBoost summary
            summary = xgboost_explainer.create_explanation_summary(request.antibiotics)
            
        elif request.model_type.lower() == "transformer":
            if transformer_explainer is None:
                raise HTTPException(status_code=500, detail="Transformer explainer not initialized")
            
            # Get transformer summary
            summary = transformer_explainer.create_explanation_summary(request.antibiotics)
            
        else:
            raise HTTPException(status_code=400, detail="Invalid model type. Use 'xgboost' or 'transformer'")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ExplanationResponse(  # type: ignore
            success=True,
            explanation=summary,  # type: ignore
            processing_time=processing_time  # type: ignore
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting explanation summary: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ExplanationResponse(  # type: ignore
            success=False,
            error=str(e),  # type: ignore
            processing_time=processing_time  # type: ignore
        )

@router.get("/models")
async def list_available_models():
    """
    List available models for explanation.
    
    Returns information about which antibiotics have trained models available.
    """
    try:
        models_info = {
            'xgboost': {
                'available': xgboost_explainer is not None,
                'models_dir': str(xgboost_explainer.models_dir) if xgboost_explainer else None
            },
            'transformer': {
                'available': transformer_explainer is not None,
                'models_dir': str(transformer_explainer.models_dir) if transformer_explainer else None
            }
        }
        
        # Try to get available antibiotics (this would require scanning model directories)
        available_antibiotics = {
            'xgboost': [],
            'transformer': []
        }
        
        # For now, return placeholder lists
        # In practice, you'd scan the model directories
        
        return {
            'success': True,
            'models_info': models_info,
            'available_antibiotics': available_antibiotics
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@router.delete("/cache")
async def clear_explanation_cache():
    """
    Clear SHAP explanation cache to free memory.
    
    Useful for long-running applications or when memory is constrained.
    """
    try:
        shap_utils.clear_cache()
        
        # Clear explainer caches
        if xgboost_explainer:
            xgboost_explainer.explainers.clear()
            xgboost_explainer.feature_names.clear()
        
        if transformer_explainer:
            transformer_explainer.explainers.clear()
            transformer_explainer.tokenizers.clear()
            transformer_explainer.models.clear()
        
        return {
            'success': True,
            'message': 'Explanation cache cleared successfully'
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# Initialize explainers when module is imported
try:
    initialize_explainers()
except Exception as e:
    logger.error(f"Failed to initialize explainers during import: {str(e)}")
