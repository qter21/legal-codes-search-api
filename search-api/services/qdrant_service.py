"""Qdrant service for semantic vector search."""
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
from loguru import logger

from config import settings


class QdrantService:
    """Service for semantic search using Qdrant."""
    
    def __init__(self):
        """Initialize Qdrant service."""
        self.url = settings.qdrant.url
        self.collection_name = settings.qdrant.collection_name
        self.client: Optional[QdrantClient] = None
    
    def connect(self) -> None:
        """Connect to Qdrant."""
        if self.client is not None:
            return
        
        logger.info(f"Connecting to Qdrant: {self.url}")
        self.client = QdrantClient(
            url=self.url,
            timeout=settings.qdrant.timeout
        )
        logger.info("Connected to Qdrant")
    
    def is_healthy(self) -> bool:
        """Check if Qdrant is healthy."""
        try:
            if not self.client:
                self.connect()
            collections = self.client.get_collections()
            return any(c.name == self.collection_name for c in collections.collections)
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    def get_point_count(self) -> int:
        """Get total point count."""
        try:
            if not self.client:
                self.connect()
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception as e:
            logger.error(f"Failed to get point count: {e}")
            return 0
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic vector search.
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Optional filters
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results
        """
        if not self.client:
            self.connect()
        
        # Build filter
        query_filter = None
        if filters:
            query_filter = self._build_filter(filters)
        
        # Set score threshold
        if score_threshold is None:
            score_threshold = settings.search.semantic.score_threshold
        
        try:
            # Execute search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit + offset,  # Fetch extra for offset
                query_filter=query_filter,
                score_threshold=score_threshold,
                with_payload=True
            )
            
            # Apply offset manually (Qdrant doesn't have native offset)
            search_results = search_results[offset:offset + limit]
            
            # Parse results
            results = []
            for scored_point in search_results:
                result = {
                    'document_id': scored_point.id,
                    'score': scored_point.score,
                    **scored_point.payload
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            raise
    
    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from filter dictionary."""
        conditions = []
        
        # Statute code exact match
        if statute_code := filters.get("statute_code"):
            conditions.append(
                FieldCondition(
                    key="statute_code",
                    match=MatchValue(value=statute_code)
                )
            )
        
        # Title contains (using keyword match on indexed field)
        if title_contains := filters.get("title_contains"):
            conditions.append(
                FieldCondition(
                    key="title",
                    match=MatchValue(value=title_contains)
                )
            )
        
        # Date range
        if filters.get("date_from") or filters.get("date_to"):
            date_range = {}
            if date_from := filters.get("date_from"):
                date_range["gte"] = date_from
            if date_to := filters.get("date_to"):
                date_range["lte"] = date_to
            
            conditions.append(
                FieldCondition(
                    key="effective_date",
                    range=Range(**date_range)
                )
            )
        
        if conditions:
            return Filter(must=conditions)
        
        return None
    
    def close(self) -> None:
        """Close Qdrant connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Closed Qdrant connection")

