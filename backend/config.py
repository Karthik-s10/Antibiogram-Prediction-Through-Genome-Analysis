"""Configuration management for the ML pipeline backend.

Loads environment variables and provides centralized config access.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_STORAGE_PATH = str(BASE_DIR / "trained_models")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars like vite_api_url
        protected_namespaces=("settings_",),  # Avoid conflict with model_storage_path
    )

    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Supabase Configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    # Application Settings
    model_storage_path: str = DEFAULT_MODEL_STORAGE_PATH
    max_upload_size_mb: int = 5000
    kmer_size_xgboost: int = 10
    kmer_size_dnabert: int = 10

    # Frontend / CORS Settings
    frontend_url: str = "http://localhost:5173"
    vite_api_url: Optional[str] = None  # Optional, so existing .env key is accepted

    # Training Settings
    train_test_split: float = 0.8
    random_seed: int = 42

    # XGBoost Defaults
    xgboost_max_depth: int = 6
    xgboost_learning_rate: float = 0.1
    xgboost_n_estimators: int = 100

    # Transformer Defaults
    # Use DNABERT v1 6-mer backbone for stable training (no remote code required)
    transformer_model_name: str = "zhihan1996/DNA_bert_6"
    transformer_max_length: int = 512
    transformer_batch_size: int = 16
    transformer_epochs: int = 3
    transformer_learning_rate: float = 2e-5

    # BLAST / explainability
    blast_mode: str = "off"  # "off", "ncbi", or "local"
    blast_local_db: Optional[str] = None
    blast_local_exe: str = "blastn"
    ncbi_email: Optional[str] = None


# Global settings instance
settings = Settings()

# Ensure model storage directory exists
os.makedirs(settings.model_storage_path, exist_ok=True)

