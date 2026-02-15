"""
API Routes for Model Explanations

Provides endpoints for generating SHAP explanations and attention visualizations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
import numpy as np
import os
from pathlib import Path
from services.explanation_service import ModelExplainer
from services.attention_service import AttentionVisualizer

router = APIRouter()

class ExplanationRequest(BaseModel):
    sample_data: Dict[str, float]  # Feature values
    sequence: Optional[str] = None  # Original DNA sequence (for attention)
    model_type: str = "xgboost"     # 'xgboost' or 'dnabert'
    class_names: Optional[List[str]] = None
    model_path: Optional[str] = None

# Initialize explainers
EXPLAINERS = {}

def get_explainer(model_path: str, feature_names: List[str], class_names: List[str], model_type: str):
    """Get or create an explainer instance."""
    key = f"{model_path}:{model_type}"
    if key not in EXPLAINERS:
        EXPLAINERS[key] = ModelExplainer(
            model_path=model_path,
            feature_names=feature_names,
            class_names=class_names,
            model_type=model_type
        )
    return EXPLAINERS[key]

@router.post("/api/explanations/generate")
async def generate_explanation(request: ExplanationRequest):
    try:
        # Set default class names if not provided
        class_names = request.class_names or ["Susceptible", "Intermediate", "Resistant"]
        
        # Get or create model path
        if request.model_path:
            model_path = request.model_path
        else:
            if request.model_type == "xgboost":
                model_path = os.getenv("XGBOOST_MODEL_PATH", "trained_models/xgboost")
            else:
                model_path = os.getenv("DNABERT_MODEL_PATH", "trained_models/dnabert")
        
        # Get feature names from sample data if not provided
        feature_names = list(request.sample_data.keys())
        
        # Get explainer
        explainer = get_explainer(
            model_path=model_path,
            feature_names=feature_names,
            class_names=class_names,
            model_type=request.model_type
        )
        
        # Convert sample data to array in the correct order
        X_sample = np.array([request.sample_data[feature] for feature in feature_names]).reshape(1, -1)
        
        # Generate explanation
        explanation = explainer.explain(X_sample, request.sequence)
        
        return {
            "status": "success",
            "explanation": explanation
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/explanations/attention")
async def get_attention_visualization(sequence: str, model_path: Optional[str] = None):
    """Get attention visualization for a DNA sequence."""
    try:
        model_path = model_path or os.getenv("DNABERT_MODEL_PATH", "trained_models/dnabert")
        visualizer = AttentionVisualizer(model_path)
        attention_data = visualizer.get_attention(sequence)
        return {"status": "success", "data": attention_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
