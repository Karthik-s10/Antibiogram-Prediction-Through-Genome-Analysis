"""
Configuration management for the ML pipeline backend.
Loads environment variables and provides centralized config access.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    
    # Supabase Configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Application Settings
    model_storage_path: str = "./trained_models"
    max_upload_size_mb: int = 5000
    kmer_size_xgboost: int = 10
    kmer_size_dnabert: int = 6
    
    # CORS Settings
    frontend_url: str = "http://localhost:5173"
    
    # Training Settings
    train_test_split: float = 0.8
    random_seed: int = 42
    
    # XGBoost Defaults
    xgboost_max_depth: int = 6
    xgboost_learning_rate: float = 0.1
    xgboost_n_estimators: int = 100
    
    # Transformer Defaults
    transformer_model_name: str = "zhihan1996/DNABERT-6"
    transformer_max_length: int = 512
    transformer_batch_size: int = 16
    transformer_epochs: int = 3
    transformer_learning_rate: float = 2e-5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Ensure model storage directory exists
os.makedirs(settings.model_storage_path, exist_ok=True)

