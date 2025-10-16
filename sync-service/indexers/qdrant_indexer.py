"""Qdrant indexer for vector embeddings."""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)
from qdrant_client.http.exceptions import UnexpectedResponse
from loguru import logger
import uuid


class QdrantIndexer:
    """Index vector embeddings to Qdrant."""
    
    def __init__(
        self,
        url: str,
        collection_name: str,
        vector_dimension: int = 384,
        batch_size: int = 100,
        timeout: int = 30
    ):
        """
        Initialize Qdrant indexer.
        
        Args:
            url: Qdrant URL
            collection_name: Name of the collection
            vector_dimension: Dimension of vectors
            batch_size: Number of points per batch
            timeout: Request timeout in seconds
        """
        self.url = url
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.batch_size = batch_size
        self.timeout = timeout
        
        self.client: Optional[QdrantClient] = None
    
    def connect(self) -> None:
        """Connect to Qdrant."""
        logger.info(f"Connecting to Qdrant: {self.url}")
        self.client = QdrantClient(
            url=self.url,
            timeout=self.timeout
        )
        logger.info("Successfully connected to Qdrant")
    
    def disconnect(self) -> None:
        """Close Qdrant connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Qdrant")
    
    def create_collection(self, recreate: bool = False) -> bool:
        """
        Create Qdrant collection with vector configuration.
        
        Args:
            recreate: If True, delete existing collection first
            
        Returns:
            True if collection was created, False if it already exists
        """
        if not self.client:
            self.connect()
        
        # Check if collection exists
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if exists:
                if recreate:
                    logger.info(f"Deleting existing collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return False
        except Exception as e:
            logger.debug(f"Error checking collection: {e}")
        
        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_dimension,
                distance=Distance.COSINE
            )
        )
        
        logger.info(f"Created collection: {self.collection_name} (dim={self.vector_dimension})")
        
        # Create payload indexes for common fields
        self._create_payload_indexes()
        
        return True
    
    def _create_payload_indexes(self) -> None:
        """Create indexes on payload fields for faster filtering."""
        if not self.client:
            self.connect()
        
        try:
            # Index statute_code as keyword
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="statute_code",
                field_schema=PayloadSchemaType.KEYWORD
            )
            
            # Index document_id as keyword
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=PayloadSchemaType.KEYWORD
            )
            
            logger.info("Created payload indexes")
        except Exception as e:
            logger.warning(f"Failed to create payload indexes: {e}")
    
    def delete_collection(self) -> None:
        """Delete the collection."""
        if not self.client:
            self.connect()
        
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except UnexpectedResponse as e:
            logger.warning(f"Collection may not exist: {e}")
    
    def index_point(
        self,
        vector: List[float],
        payload: Dict[str, Any],
        point_id: Optional[str] = None
    ) -> None:
        """
        Index a single point (vector + payload).
        
        Args:
            vector: Embedding vector
            payload: Metadata payload
            point_id: Optional point ID (generated if not provided)
        """
        if not self.client:
            self.connect()
        
        if not point_id:
            point_id = str(uuid.uuid4())
        
        point = PointStruct(
            id=point_id,
            vector=vector,
            payload=payload
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def index_batch(
        self,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        point_ids: Optional[List[str]] = None
    ) -> tuple[int, int]:
        """
        Index a batch of points using batch API.
        
        Args:
            vectors: List of embedding vectors
            payloads: List of metadata payloads
            point_ids: Optional list of point IDs
            
        Returns:
            Tuple of (success_count, error_count)
        """
        if not self.client:
            self.connect()
        
        if not vectors or not payloads:
            return 0, 0
        
        if len(vectors) != len(payloads):
            logger.error("Vectors and payloads must have same length")
            return 0, len(vectors)
        
        # Generate IDs if not provided
        if not point_ids:
            point_ids = [payload.get("document_id") or str(uuid.uuid4()) 
                        for payload in payloads]
        
        # Create points
        points = [
            PointStruct(
                id=str(point_id),
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(point_ids, vectors, payloads)
        ]
        
        try:
            # Upload points in batches
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.debug(f"Indexed {len(points)} vectors to Qdrant")
            return len(points), 0
            
        except Exception as e:
            logger.error(f"Failed to index batch: {e}")
            return 0, len(vectors)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get collection information.
        
        Returns:
            Collection info dictionary
        """
        if not self.client:
            self.connect()
        
        info = self.client.get_collection(self.collection_name)
        return {
            "name": info.config.params.vectors.size,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
        }
    
    def get_point_count(self) -> int:
        """
        Get total point count in collection.
        
        Returns:
            Number of points
        """
        if not self.client:
            self.connect()
        
        info = self.client.get_collection(self.collection_name)
        return info.points_count or 0
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

