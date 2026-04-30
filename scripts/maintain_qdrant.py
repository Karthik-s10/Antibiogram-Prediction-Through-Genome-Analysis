#!/usr/bin/env python3
"""
Qdrant Collection Maintenance Script

This script ensures the Qdrant collection remains active and prevents auto-deletion.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests  # type: ignore
from qdrant_client import QdrantClient  # type: ignore
from qdrant_client.http import models  # type: ignore
from dotenv import load_dotenv  # type: ignore

# Configure logging
log_file = f"qdrant_maintenance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QdrantMaintainer:
    def __init__(self):
        load_dotenv()
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("COLLECTION_NAME", "bacterial_genomes")
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.notify_on_failure = os.getenv("NOTIFY_ON_FAILURE", "true").lower() == "true"
        
        if not all([self.qdrant_url, self.api_key]):
            raise ValueError("QDRANT_URL and QDRANT_API_KEY environment variables are required")
            
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.api_key,
            timeout=30
        )
        
    def check_collection_exists(self) -> bool:
        try:
            collections = self.client.get_collections()
            return any(c.name == self.collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"Failed to check collection: {e}")
            return False
            
    def get_collection_info(self) -> Optional[Dict[str, Any]]:
        try:
            collection = self.client.get_collection(self.collection_name)
            return {
                "status": "exists",
                "vectors_count": collection.vectors_count,
                "points_count": collection.points_count,
                "config": collection.config.dict() if collection.config else None
            }
        except Exception as e:
            logger.warning(f"Failed to get collection info via QdrantClient: {e}")
            logger.info("Falling back to raw HTTP request...")
            try:
                headers = {"api-key": self.api_key} if self.api_key else {}
                res = requests.get(
                    f"{self.qdrant_url}/collections/{self.collection_name}",
                    headers=headers,
                    timeout=10
                )
                res.raise_for_status()
                data = res.json().get("result", {})
                return {
                    "status": "exists",
                    "vectors_count": data.get("vectors_count"),
                    "points_count": data.get("points_count"),
                    "config": data.get("config")
                }
            except Exception as req_e:
                logger.error(f"Fallback HTTP request to get info failed: {req_e}")
            return None
            
    def perform_health_check(self) -> bool:
        try:
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=1,
                with_vectors=False,
                with_payload=False
            )
            return len(points[0]) > 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
            
    def update_collection_ttl(self) -> bool:
        if self.dry_run:
            logger.info("[DRY RUN] Would update collection TTL")
            return True
            
        try:
            self.client.update_collection(
                collection_name=self.collection_name,
                optimizers_config=models.OptimizersConfigDiff()
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to update collection TTL via QdrantClient: {e}")
            logger.info("Falling back to raw HTTP request...")
            try:
                headers = {"api-key": self.api_key, "Content-Type": "application/json"} if self.api_key else {"Content-Type": "application/json"}
                payload = {"optimizers_config": {}}
                res = requests.patch(
                    f"{self.qdrant_url}/collections/{self.collection_name}",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                res.raise_for_status()
                return True
            except Exception as req_e:
                logger.error(f"Fallback HTTP request to update TTL failed: {req_e}")
            return False
            
    def send_notification(self, success: bool, message: str):
        """Send notification using GitHub Actions workflow commands"""
        if success:
            logger.info(f"✅ {message}")
            print(f"::notice::{message}")
        else:
            logger.error(f"❌ {message}")
            if self.notify_on_failure:
                print(f"::error::{message}")
                
    def run(self):
        logger.info(f"🚀 Starting Qdrant collection maintenance for '{self.collection_name}'")
        
        if not self.check_collection_exists():
            error_msg = f"Collection '{self.collection_name}' does not exist"
            self.send_notification(False, error_msg)
            raise ValueError(error_msg)
            
        info = self.get_collection_info()
        if not info:
            error_msg = f"Failed to get info for collection '{self.collection_name}'"
            self.send_notification(False, error_msg)
            raise RuntimeError(error_msg)
            
        logger.info(f"📊 Collection info: {info}")
        
        if not self.perform_health_check():
            error_msg = f"Health check failed for collection '{self.collection_name}'"
            self.send_notification(False, error_msg)
            raise RuntimeError(error_msg)
            
        if not self.update_collection_ttl():
            error_msg = f"Failed to update TTL for collection '{self.collection_name}'"
            self.send_notification(False, error_msg)
            raise RuntimeError(error_msg)
            
        success_msg = (
            f"Successfully maintained collection '{self.collection_name}'. "
            f"Points: {info.get('points_count', 'N/A')}, "
            f"Vectors: {info.get('vectors_count', 'N/A')}"
        )
        self.send_notification(True, success_msg)
        logger.info("✅ Maintenance completed successfully")

if __name__ == "__main__":
    try:
        maintainer = QdrantMaintainer()
        maintainer.run()
    except Exception as e:
        logger.critical(f"🚨 Maintenance failed: {e}")
        exit(1)
