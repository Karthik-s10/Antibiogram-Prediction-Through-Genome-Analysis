"""
Qdrant vector database service for genome similarity search.
Manages vector embeddings and similarity queries.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import logging

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Qdrant client not installed. Vector search will not be available.")

from config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """
    Service for managing genome embeddings in Qdrant vector database.
    Handles collection creation, vector insertion, and similarity search.
    """
    
    COLLECTION_NAME = "bacterial_genomes"
    VECTOR_SIZE = 768  # Standard embedding dimension
    
    def __init__(self):
        """Initialize Qdrant client."""
        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant client not available")
            self.client = None
            return
        
        try:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
            logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
            
            # Ensure collection exists
            self._ensure_collection()
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.client = None
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        if not self.client:
            return
        
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.COLLECTION_NAME not in collection_names:
                self.client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")
            else:
                logger.info(f"Qdrant collection already exists: {self.COLLECTION_NAME}")
                
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
    
    def insert_genome_embedding(
        self,
        genome_id: str,
        embedding: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Insert a genome embedding into Qdrant.
        
        Args:
            genome_id: Unique genome identifier
            embedding: Vector embedding (must be VECTOR_SIZE dimensions)
            metadata: Additional metadata (species, model_path, etc.)
        
        Returns:
            True if successful
        """
        if not self.client:
            logger.warning("Qdrant client not available")
            return False
        
        try:
            # Ensure embedding is the right size
            if len(embedding) != self.VECTOR_SIZE:
                # Pad or truncate if needed
                if len(embedding) < self.VECTOR_SIZE:
                    embedding = np.pad(embedding, (0, self.VECTOR_SIZE - len(embedding)))
                else:
                    embedding = embedding[:self.VECTOR_SIZE]
            
            # Create payload
            payload = metadata or {}
            payload['genome_id'] = genome_id
            
            # Insert point
            point = PointStruct(
                id=hash(genome_id) & 0x7FFFFFFF,  # Positive integer ID
                vector=embedding.tolist(),
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point]
            )
            
            logger.info(f"Inserted embedding for genome: {genome_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting embedding: {e}")
            return False
    
    def batch_insert_embeddings(
        self,
        genome_ids: List[str],
        embeddings: np.ndarray,
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        Batch insert multiple genome embeddings.
        
        Args:
            genome_ids: List of genome identifiers
            embeddings: Array of embeddings (n_genomes × VECTOR_SIZE)
            metadata_list: Optional list of metadata dicts
        
        Returns:
            Number of successfully inserted embeddings
        """
        if not self.client:
            logger.warning("Qdrant client not available")
            return 0
        
        if metadata_list is None:
            metadata_list = [{}] * len(genome_ids)
        
        points = []
        for i, genome_id in enumerate(genome_ids):
            embedding = embeddings[i]
            metadata = metadata_list[i]
            
            # Ensure embedding size
            if len(embedding) != self.VECTOR_SIZE:
                if len(embedding) < self.VECTOR_SIZE:
                    embedding = np.pad(embedding, (0, self.VECTOR_SIZE - len(embedding)))
                else:
                    embedding = embedding[:self.VECTOR_SIZE]
            
            payload = metadata.copy()
            payload['genome_id'] = genome_id
            
            point = PointStruct(
                id=hash(genome_id) & 0x7FFFFFFF,
                vector=embedding.tolist(),
                payload=payload
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points
            )
            logger.info(f"Batch inserted {len(points)} embeddings")
            return len(points)
            
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            return 0
    
    def search_similar_genomes(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar genomes in the database.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
        
        Returns:
            List of similar genomes with scores and metadata
        """
        if not self.client:
            logger.warning("Qdrant client not available")
            return []
        
        try:
            # Ensure embedding size
            if len(query_embedding) != self.VECTOR_SIZE:
                if len(query_embedding) < self.VECTOR_SIZE:
                    query_embedding = np.pad(query_embedding, (0, self.VECTOR_SIZE - len(query_embedding)))
                else:
                    query_embedding = query_embedding[:self.VECTOR_SIZE]
            
            # Search
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding.tolist(),
                limit=top_k
            )
            
            # Format results and deduplicate by genome_id so the same genome
            # does not appear multiple times even if Qdrant contains multiple
            # points with identical genome_id payloads.
            similar_genomes = []
            seen_ids = set()
            for result in results:
                genome_id = result.payload.get('genome_id')
                if genome_id in seen_ids:
                    continue
                seen_ids.add(genome_id)

                similar_genomes.append({
                    'genome_id': genome_id,
                    'score': result.score,
                    'metadata': result.payload
                })
            
            logger.info(f"Found {len(similar_genomes)} similar genomes")
            return similar_genomes
            
        except Exception as e:
            logger.error(f"Error searching similar genomes: {e}")
            return []
    
    def delete_genome(self, genome_id: str) -> bool:
        """
        Delete a genome embedding from the database.
        
        Args:
            genome_id: Genome identifier
        
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            point_id = hash(genome_id) & 0x7FFFFFFF
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[point_id]
            )
            logger.info(f"Deleted genome: {genome_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting genome: {e}")
            return False
    
    def genome_exists(self, genome_id: str) -> bool:
        """
        Check if a specific genome already exists in the collection.
        
        Args:
            genome_id: Genome identifier
            
        Returns:
            True if genome exists
        """
        if not self.client:
            return False
        
        try:
            # Use the same ID scheme as insert_genome_embedding/delete_genome
            point_id = hash(genome_id) & 0x7FFFFFFF
            results = self.client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[point_id]
            )
            return len(results) > 0
        except Exception as e:
            logger.error(f"Failed to check if genome exists: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection stats
        """
        if not self.client:
            return {"error": "Qdrant not available"}

        # Use a raw HTTP request instead of qdrant_client.get_collection to
        # avoid pydantic model validation issues with newer Qdrant Cloud
        # response fields.
        try:
            import httpx

            base_url = settings.qdrant_url.rstrip("/")
            # If URL already has an explicit port, don't append :6333 again
            has_port = False
            try:
                # Split off scheme
                without_scheme = base_url.split("//", 1)[-1]
                host_port = without_scheme.rsplit(":", 1)
                if len(host_port) == 2 and host_port[1].isdigit():
                    has_port = True
            except Exception:
                has_port = False

            if has_port:
                url = f"{base_url}/collections/{self.COLLECTION_NAME}"
            else:
                url = f"{base_url}:6333/collections/{self.COLLECTION_NAME}"

            headers = {}
            if settings.qdrant_api_key:
                headers["api-key"] = settings.qdrant_api_key

            resp = httpx.get(url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", {})
            return {
                "collection_name": result.get("name", self.COLLECTION_NAME),
                "vectors_count": result.get("vectors_count"),
                "points_count": result.get("points_count"),
                "status": result.get("status"),
            }
        except Exception as e:
            logger.warning(f"Error getting collection stats via HTTP: {e}")
            return {"error": str(e)}

