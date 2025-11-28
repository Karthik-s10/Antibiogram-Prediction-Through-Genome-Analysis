"""
Test script for Qdrant connection
Verifies that the Qdrant Cloud instance is accessible and the collection exists.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.qdrant_service import QdrantService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Test Qdrant connection and collection."""
    
    logger.info("=" * 80)
    logger.info("QDRANT CONNECTION TEST")
    logger.info("=" * 80)
    
    try:
        # Initialize Qdrant service
        logger.info("\n1. Initializing Qdrant service...")
        qdrant_service = QdrantService()
        
        if not qdrant_service.client:
            logger.error("   ✗ Qdrant client not available. Check your configuration.")
            return
        
        logger.info("   ✓ Qdrant service initialized")
        
        # Get collection stats
        logger.info("\n2. Getting collection stats...")
        stats = qdrant_service.get_collection_stats()
        
        if "error" not in stats:
            logger.info(f"   ✓ Collection '{stats.get('collection_name')}' accessible")
            logger.info(f"   - Vectors count: {stats.get('vectors_count')}")
            logger.info(f"   - Points count: {stats.get('points_count')}")
            logger.info(f"   - Status: {stats.get('status')}")
        else:
            logger.warning(f"   Collection stats error: {stats.get('error')}")
        
        # Test upsert with a dummy vector
        logger.info("\n3. Testing upsert with a dummy genome...")
        import numpy as np
        
        test_genome_id = "TEST_GENOME_001"
        test_embedding = np.array([0.1] * 768, dtype=np.float32)  # 768-dim dummy vector
        test_metadata = {
            "antibiotic_labels": {"amikacin": "S", "ampicillin": "R"},
            "species": "Test Species"
        }
        
        success = qdrant_service.insert_genome_embedding(
            genome_id=test_genome_id,
            embedding=test_embedding,
            metadata=test_metadata
        )
        
        if success:
            logger.info("   ✓ Test genome upserted successfully!")
        else:
            logger.error("   ✗ Failed to upsert test genome")
            return
        
        # Test genome_exists
        logger.info("\n4. Testing genome_exists check...")
        if qdrant_service.genome_exists(test_genome_id):
            logger.info("   ✓ genome_exists returned True for existing genome")
        else:
            logger.error("   ✗ genome_exists returned False for existing genome")
            
        if not qdrant_service.genome_exists("NON_EXISTENT_GENOME"):
            logger.info("   ✓ genome_exists returned False for non-existent genome")
        else:
            logger.error("   ✗ genome_exists returned True for non-existent genome")
        
        # Test search
        logger.info("\n5. Testing similarity search...")
        results = qdrant_service.search_similar_genomes(
            query_embedding=test_embedding,
            top_k=5
        )
        logger.info(f"   ✓ Search returned {len(results)} results")
        
        if results:
            logger.info("\n   Top result:")
            top = results[0]
            logger.info(f"   - Genome ID: {top['genome_id']}")
            logger.info(f"   - Score: {top['score']:.4f}")
            logger.info(f"   - Metadata: {top['metadata']}")
        
        # Clean up test genome
        logger.info("\n6. Cleaning up test genome...")
        qdrant_service.delete_genome(test_genome_id)
        logger.info("   ✓ Test genome deleted")
        
        # Final status
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL QDRANT TESTS PASSED!")
        logger.info("=" * 80)
        logger.info("\nQdrant is properly configured and ready for use.")
        logger.info("When you run training, genome embeddings will be stored automatically.")
        
    except Exception as e:
        logger.error(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
        logger.info("\nTroubleshooting:")
        logger.info("1. Check that backend/.env exists with correct QDRANT_URL and QDRANT_API_KEY")
        logger.info("2. Verify your Qdrant Cloud instance is running")
        logger.info("3. Check that the API key has write permissions")


if __name__ == "__main__":
    main()
