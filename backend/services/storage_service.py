"""
Model storage service for saving and loading trained models.
Supports local filesystem with cloud storage integration ready.
"""
import os
import shutil
import json
from typing import Optional, Dict, Any
from pathlib import Path
import logging

from config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Manages storage and retrieval of trained models.
    Currently uses local filesystem, designed for easy cloud migration.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize storage service.
        
        Args:
            storage_path: Base path for model storage (defaults to settings)
        """
        self.storage_path = storage_path or settings.model_storage_path
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"Initialized storage service at: {self.storage_path}")
    
    def save_model_artifact(
        self,
        model_name: str,
        artifact_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a model artifact (model file, feature dict, etc.).
        
        Args:
            model_name: Name of the model
            artifact_type: Type of artifact (e.g., 'model', 'features', 'metadata')
            content: Binary content to save
            metadata: Optional metadata to save alongside
        
        Returns:
            Path to saved artifact
        """
        # Create model directory
        model_dir = os.path.join(self.storage_path, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        # Determine file extension based on type
        ext_map = {
            'model': '.pkl',
            'features': '.json',
            'metadata': '.json',
            'tokenizer': '.json',
            'checkpoint': '.pt'
        }
        ext = ext_map.get(artifact_type, '.bin')
        
        # Save artifact
        artifact_path = os.path.join(model_dir, f"{artifact_type}{ext}")
        
        with open(artifact_path, 'wb') as f:
            f.write(content)
        
        # Save metadata if provided
        if metadata:
            metadata_path = os.path.join(model_dir, f"{artifact_type}_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved {artifact_type} artifact for {model_name} at {artifact_path}")
        
        return artifact_path
    
    def load_model_artifact(
        self,
        model_name: str,
        artifact_type: str
    ) -> bytes:
        """
        Load a model artifact.
        
        Args:
            model_name: Name of the model
            artifact_type: Type of artifact to load
        
        Returns:
            Binary content of artifact
        """
        model_dir = os.path.join(self.storage_path, model_name)
        
        # Try different extensions
        ext_map = {
            'model': '.pkl',
            'features': '.json',
            'metadata': '.json',
            'tokenizer': '.json',
            'checkpoint': '.pt'
        }
        ext = ext_map.get(artifact_type, '.bin')
        
        artifact_path = os.path.join(model_dir, f"{artifact_type}{ext}")
        
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")
        
        with open(artifact_path, 'rb') as f:
            content = f.read()
        
        logger.info(f"Loaded {artifact_type} artifact for {model_name}")
        
        return content
    
    def list_models(self) -> list[Dict[str, Any]]:
        """
        List all stored models.
        
        Returns:
            List of model information dictionaries
        """
        models = []
        
        if not os.path.exists(self.storage_path):
            return models
        
        for item in os.listdir(self.storage_path):
            model_dir = os.path.join(self.storage_path, item)
            
            if os.path.isdir(model_dir):
                # Try to load metadata
                metadata_path = os.path.join(model_dir, 'metadata.json')
                
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        
                        models.append({
                            'model_name': item,
                            'model_dir': model_dir,
                            'metadata': metadata
                        })
                    except:
                        pass
                else:
                    # Basic info without metadata
                    models.append({
                        'model_name': item,
                        'model_dir': model_dir,
                        'metadata': {}
                    })
        
        return models
    
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a stored model.
        
        Args:
            model_name: Name of the model to delete
        
        Returns:
            True if deleted successfully
        """
        model_dir = os.path.join(self.storage_path, model_name)
        
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
            logger.info(f"Deleted model: {model_name}")
            return True
        
        logger.warning(f"Model not found for deletion: {model_name}")
        return False
    
    def get_model_path(self, model_name: str) -> str:
        """
        Get the full path to a model directory.
        
        Args:
            model_name: Name of the model
        
        Returns:
            Full path to model directory
        """
        return os.path.join(self.storage_path, model_name)
    
    # TODO: Cloud storage integration methods
    
    def upload_to_cloud(self, model_name: str, cloud_provider: str = 's3'):
        """
        Upload model to cloud storage (S3, Azure Blob, etc.).
        To be implemented when cloud deployment is needed.
        
        Args:
            model_name: Name of the model
            cloud_provider: Cloud provider ('s3', 'azure', 'gcs')
        """
        raise NotImplementedError("Cloud upload not yet implemented")
    
    def download_from_cloud(self, model_name: str, cloud_provider: str = 's3'):
        """
        Download model from cloud storage.
        To be implemented when cloud deployment is needed.
        
        Args:
            model_name: Name of the model
            cloud_provider: Cloud provider ('s3', 'azure', 'gcs')
        """
        raise NotImplementedError("Cloud download not yet implemented")

