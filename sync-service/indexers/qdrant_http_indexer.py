"""HTTP-based Qdrant indexer (bypasses qdrant-client library issues)."""
import requests
import uuid
import json
from typing import List, Dict, Any, Tuple
from loguru import logger


class QdrantHTTPIndexer:
    """Qdrant indexer using direct HTTP API."""
    
    def __init__(self, url: str, collection_name: str, vector_dimension: int):
        """
        Initialize HTTP-based Qdrant indexer.
        
        Args:
            url: Qdrant server URL
            collection_name: Name of the collection
            vector_dimension: Dimension of vectors
        """
        self.url = url.rstrip('/')
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.session = requests.Session()
        logger.info(f"Initialized Qdrant HTTP indexer: {url}/{collection_name}")
    
    def connect(self) -> bool:
        """Test connection to Qdrant."""
        try:
            response = self.session.get(f"{self.url}/")
            response.raise_for_status()
            info = response.json()
            logger.info(f"Connected to Qdrant {info.get('version', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close the session."""
        self.session.close()
        logger.info("Disconnected from Qdrant")
    
    def ensure_collection(self) -> bool:
        """Ensure collection exists."""
        try:
            # Check if collection exists
            response = self.session.get(f"{self.url}/collections/{self.collection_name}")
            if response.status_code == 200:
                logger.info(f"Collection {self.collection_name} exists")
                return True
            
            # Create collection
            response = self.session.put(
                f"{self.url}/collections/{self.collection_name}",
                json={
                    "vectors": {
                        "size": self.vector_dimension,
                        "distance": "Cosine"
                    }
                }
            )
            response.raise_for_status()
            logger.info(f"Created collection {self.collection_name} (dim={self.vector_dimension})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            return False
    
    def index_batch(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        point_ids: List[str]
    ) -> Tuple[int, int]:
        """
        Index a batch of vectors.
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata payloads
            point_ids: List of point IDs
        
        Returns:
            Tuple of (success_count, error_count)
        """
        if not vectors or not payloads or not point_ids:
            return 0, 0
        
        if len(vectors) != len(payloads) != len(point_ids):
            logger.error(f"Length mismatch: vectors={len(vectors)}, payloads={len(payloads)}, ids={len(point_ids)}")
            return 0, len(vectors)
        
        # Prepare points
        points = []
        for i, (vector, payload, point_id) in enumerate(zip(vectors, payloads, point_ids)):
            # Validate
            if not isinstance(vector, list):
                logger.error(f"Point {i}: vector is not a list")
                continue
            
            if len(vector) != self.vector_dimension:
                logger.error(f"Point {i}: wrong dimension {len(vector)}, expected {self.vector_dimension}")
                continue
            
            # Use hash of ID as integer (Qdrant requires integer or UUID)
            # Convert string ID to stable integer using hash
            id_hash = hash(str(point_id)) & 0x7FFFFFFFFFFFFFFF  # Positive 63-bit integer
            points.append({
                "id": id_hash,
                "vector": vector,
                "payload": {
                    **payload,
                    "document_id": str(point_id)  # Keep original ID in payload
                }
            })
        
        if not points:
            logger.error("No valid points to index")
            return 0, len(vectors)
        
        try:
            # Debug: log first point
            if points:
                first_point = points[0]
                logger.debug(f"Sample point - ID: {first_point['id']}, Vector len: {len(first_point['vector'])}, Payload keys: {list(first_point['payload'].keys())}")
            
            # Batch upsert using HTTP API
            payload_data = {"points": points}
            response = self.session.put(
                f"{self.url}/collections/{self.collection_name}/points",
                json=payload_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Indexed {len(points)} points to Qdrant (operation_id: {result.get('result', {}).get('operation_id')})")
                return len(points), len(vectors) - len(points)
            else:
                logger.error(f"Failed to index: {response.status_code} - {response.text}")
                # Debug: log the data being sent
                logger.error(f"First point data: {json.dumps(points[0] if points else {}, indent=2)}")
                return 0, len(vectors)
                
        except Exception as e:
            logger.error(f"Exception during indexing: {e}")
            return 0, len(vectors)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            response = self.session.get(f"{self.url}/collections/{self.collection_name}")
            response.raise_for_status()
            return response.json().get("result", {})
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}

