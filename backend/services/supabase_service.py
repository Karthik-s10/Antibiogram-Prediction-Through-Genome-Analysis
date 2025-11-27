"""
Supabase service for storing model metadata and training history.
Provides database operations for model registry and genome information.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """
    Service for managing model metadata in Supabase.
    Handles model registry and genome embedding metadata.
    """
    
    def __init__(self):
        """Initialize Supabase client."""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase client not installed")
            self.client = None
            return
        
        if not settings.supabase_url or not settings.supabase_key:
            logger.warning("Supabase credentials not configured")
            self.client = None
            return
        
        try:
            self.client: Client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            self.client = None
    
    def register_model(
        self,
        model_name: str,
        model_type: str,
        file_path: str,
        metrics: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Register a trained model in the database.
        
        Args:
            model_name: Name of the model
            model_type: Type ('xgboost' or 'transformer')
            file_path: Path to model file
            metrics: Training metrics
            metadata: Additional metadata
        
        Returns:
            Model ID if successful, None otherwise
        """
        if not self.client:
            logger.warning("Supabase not available, skipping model registration")
            return None
        
        try:
            data = {
                'model_name': model_name,
                'model_type': model_type,
                'file_path': file_path,
                'metrics': metrics,
                'metadata': metadata or {},
                'training_date': datetime.now().isoformat(),
                'status': 'trained'
            }
            
            result = self.client.table('trained_models').insert(data).execute()
            
            if result.data:
                model_id = result.data[0]['id']
                logger.info(f"Registered model: {model_name} (ID: {model_id})")
                return model_id
            
        except Exception as e:
            logger.error(f"Error registering model: {e}")
        
        return None
    
    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve model information by name.
        
        Args:
            model_name: Name of the model
        
        Returns:
            Model information dict or None
        """
        if not self.client:
            return None
        
        try:
            result = self.client.table('trained_models')\
                .select('*')\
                .eq('model_name', model_name)\
                .order('training_date', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            
        except Exception as e:
            logger.error(f"Error retrieving model: {e}")
        
        return None
    
    def list_models(
        self,
        model_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all trained models.
        
        Args:
            model_type: Optional filter by type
            limit: Maximum number of models to return
        
        Returns:
            List of model information dicts
        """
        if not self.client:
            return []
        
        try:
            query = self.client.table('trained_models').select('*')
            
            if model_type:
                query = query.eq('model_type', model_type)
            
            result = query.order('training_date', desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def register_genome_embedding(
        self,
        genome_id: str,
        species: str,
        embedding_id: int,
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Register a genome embedding in the database.
        
        Args:
            genome_id: Genome identifier
            species: Bacterial species
            embedding_id: Qdrant point ID
            model_name: Associated model name
            metadata: Additional metadata
        
        Returns:
            Record ID if successful
        """
        if not self.client:
            logger.warning("Supabase not available, skipping genome registration")
            return None
        
        try:
            data = {
                'genome_id': genome_id,
                'species': species,
                'embedding_id': embedding_id,
                'model_name': model_name,
                'metadata': metadata or {},
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('genome_embeddings').insert(data).execute()
            
            if result.data:
                record_id = result.data[0]['id']
                logger.info(f"Registered genome embedding: {genome_id}")
                return record_id
            
        except Exception as e:
            logger.error(f"Error registering genome embedding: {e}")
        
        return None
    
    def update_model_status(
        self,
        model_name: str,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """
        Update model training status.
        
        Args:
            model_name: Name of the model
            status: New status
            error: Optional error message
        
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            update_data = {'status': status}
            if error:
                update_data['error'] = error
            
            self.client.table('trained_models')\
                .update(update_data)\
                .eq('model_name', model_name)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating model status: {e}")
            return False

