"""
Qdrant Service for Genome Embeddings
Handles storage and retrieval of genome embeddings for similarity search.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class QdrantService:
    """
    Service for storing and searching genome embeddings in Qdrant.
    
    Uses DNABERT embeddings (768 dimensions) for similarity search.
    """
    
    VECTOR_SIZE = 768  # DNABERT-6 output dimension
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initialize Qdrant client.
        
        Args:
            url: Qdrant server URL (defaults to env QDRANT_URL)
            api_key: Qdrant API key (defaults to env QDRANT_API_KEY)
            collection_name: Collection name (defaults to env QDRANT_COLLECTION_NAME)
        """
        self.url = url or os.getenv("QDRANT_URL")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION_NAME", "genomic_amr_vectors")
        
        if not self.url:
            raise ValueError("QDRANT_URL not set. Check your .env file.")
        
        logger.info(f"Connecting to Qdrant at {self.url}")
        
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=60
        )
        
        logger.info("Qdrant client initialized successfully")
    
    def test_connection(self) -> bool:
        """
        Test connection to Qdrant server.
        
        Returns:
            True if connection successful
        """
        try:
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant. Collections: {[c.name for c in collections.collections]}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return False
    
    def collection_exists(self) -> bool:
        """
        Check if the collection exists.
        
        Returns:
            True if collection exists
        """
        try:
            collections = self.client.get_collections()
            return any(c.name == self.collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"Error checking collection: {e}")
            return False
    
    def create_collection(self, recreate: bool = False) -> bool:
        """
        Create the genome embeddings collection.
        
        Args:
            recreate: If True, delete existing collection first
            
        Returns:
            True if successful
        """
        try:
            if recreate and self.collection_exists():
                logger.info(f"Deleting existing collection: {self.collection_name}")
                self.client.delete_collection(self.collection_name)
            
            if not self.collection_exists():
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False
    
    def genome_exists(self, genome_id: str) -> bool:
        """
        Check if a specific genome already exists in the collection.
        
        Args:
            genome_id: Genome identifier
            
        Returns:
            True if genome exists
        """
        try:
            point_id = abs(hash(genome_id)) % (10 ** 12)
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            return len(results) > 0
        except Exception as e:
            logger.error(f"Failed to check if genome exists: {e}")
            return False

    def upsert_genomes(
        self,
        genome_ids: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Insert or update genome embeddings in Qdrant.
        
        Args:
            genome_ids: List of genome identifiers (GenBank accessions)
            embeddings: List of embedding vectors (768-dim each)
            metadata: Optional list of metadata dicts per genome
                      (e.g., {"antibiotic_labels": {...}, "species": "..."})
        
        Returns:
            True if successful
        """
        if len(genome_ids) != len(embeddings):
            raise ValueError("genome_ids and embeddings must have same length")
        
        if metadata and len(metadata) != len(genome_ids):
            raise ValueError("metadata must have same length as genome_ids")
        
        logger.info(f"Upserting {len(genome_ids)} genomes to Qdrant")
        
        try:
            # Ensure collection exists
            self.create_collection()
            
            # Build points
            points = []
            for i, (gid, emb) in enumerate(zip(genome_ids, embeddings)):
                payload = {
                    "genome_id": gid,
                }
                if metadata and metadata[i]:
                    payload.update(metadata[i])
                
                # Use hash of genome_id as point ID (Qdrant needs int or UUID)
                point_id = abs(hash(gid)) % (10 ** 12)
                
                points.append(PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=payload
                ))
            
            # Upsert in batches of 100
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.info(f"Upserted batch {i // batch_size + 1}/{(len(points) - 1) // batch_size + 1}")
            
            logger.info(f"Successfully upserted {len(genome_ids)} genomes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert genomes: {e}")
            raise
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar genomes.
        
        Args:
            query_embedding: 768-dim embedding of query genome
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1 for cosine)
            
        Returns:
            List of results with genome_id, score, and metadata
        """
        logger.info(f"Searching for {top_k} similar genomes")
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            similar_genomes = []
            for hit in results:
                similar_genomes.append({
                    "genome_id": hit.payload.get("genome_id"),
                    "score": hit.score,
                    "metadata": hit.payload
                })
            
            logger.info(f"Found {len(similar_genomes)} similar genomes")
            return similar_genomes
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Collection info dict
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "vector_size": self.VECTOR_SIZE
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"error": str(e)}
    
    def delete_genome(self, genome_id: str) -> bool:
        """
        Delete a genome from the collection.
        
        Args:
            genome_id: Genome identifier to delete
            
        Returns:
            True if successful
        """
        try:
            point_id = abs(hash(genome_id)) % (10 ** 12)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[point_id])
            )
            logger.info(f"Deleted genome {genome_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete genome: {e}")
            return False
