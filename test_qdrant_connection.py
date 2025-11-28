"""
Test script for Qdrant connection
Verifies that the Qdrant Cloud instance is accessible and the collection exists.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.services.qdrant_service import QdrantService

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
        logger.info("   ✓ Qdrant service initialized")
        
        # Test connection
        logger.info("\n2. Testing connection to Qdrant Cloud...")
        if qdrant_service.test_connection():
            logger.info("   ✓ Connection successful!")
        else:
            logger.error("   ✗ Connection failed!")
            return
        
        # Check if collection exists
        logger.info(f"\n3. Checking if collection '{qdrant_service.collection_name}' exists...")
        if qdrant_service.collection_exists():
            logger.info("   ✓ Collection exists!")
            
            # Get collection info
            info = qdrant_service.get_collection_info()
            logger.info(f"\n   Collection Info:")
            logger.info(f"   - Name: {info.get('name')}")
            logger.info(f"   - Vectors count: {info.get('vectors_count')}")
            logger.info(f"   - Points count: {info.get('points_count')}")
            logger.info(f"   - Status: {info.get('status')}")
            logger.info(f"   - Vector size: {info.get('vector_size')}")
        else:
            logger.info("   ✗ Collection does not exist yet")
            logger.info("\n4. Creating collection...")
            if qdrant_service.create_collection():
                logger.info("   ✓ Collection created successfully!")
            else:
                logger.error("   ✗ Failed to create collection")
                return
        
        # Test upsert with a dummy vector
        logger.info("\n5. Testing upsert with a dummy genome...")
        test_genome_id = "TEST_GENOME_001"
        test_embedding = [0.1] * 768  # 768-dim dummy vector
        test_metadata = {
            "antibiotic_labels": {"amikacin": 0, "ampicillin": 2},
            "species": "Test Species"
        }
        
        qdrant_service.upsert_genomes(
            genome_ids=[test_genome_id],
            embeddings=[test_embedding],
            metadata=[test_metadata]
        )
        logger.info("   ✓ Test genome upserted successfully!")
        
        # Test genome_exists
        logger.info("\n6a. Testing genome_exists check...")
        if qdrant_service.genome_exists(test_genome_id):
            logger.info("   ✓ genome_exists returned True for existing genome")
        else:
            logger.error("   ✗ genome_exists returned False for existing genome")
            
        if not qdrant_service.genome_exists("NON_EXISTENT_GENOME"):
            logger.info("   ✓ genome_exists returned False for non-existent genome")
        else:
            logger.error("   ✗ genome_exists returned True for non-existent genome")
        
        # Test search
        logger.info("\n6b. Testing similarity search...")
        results = qdrant_service.search_similar(
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
        logger.info("\n7. Cleaning up test genome...")
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
