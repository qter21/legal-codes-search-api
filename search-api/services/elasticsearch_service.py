"""Elasticsearch service for keyword search."""
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from loguru import logger

from config import settings


class ElasticsearchService:
    """Service for keyword-based search using Elasticsearch."""
    
    def __init__(self):
        """Initialize Elasticsearch service."""
        self.url = settings.elasticsearch.url
        self.index_name = settings.elasticsearch.index_name
        self.client: Optional[Elasticsearch] = None
    
    def connect(self) -> None:
        """Connect to Elasticsearch."""
        if self.client is not None:
            return
        
        logger.info(f"Connecting to Elasticsearch: {self.url}")
        self.client = Elasticsearch(
            [self.url],
            request_timeout=settings.elasticsearch.timeout,
            max_retries=settings.elasticsearch.max_retries,
            retry_on_timeout=True
        )
        
        if not self.client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
        
        logger.info("Connected to Elasticsearch")
    
    def is_healthy(self) -> bool:
        """Check if Elasticsearch is healthy."""
        try:
            if not self.client:
                self.connect()
            return self.client.ping()
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get total document count."""
        try:
            if not self.client:
                self.connect()
            result = self.client.count(index=self.index_name)
            return result['count']
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
    
    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        fuzziness: str = "AUTO",
        boost_exact: bool = True
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Perform keyword search.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            offset: Number of results to skip
            fields: Fields to search in
            filters: Optional filters
            fuzziness: Fuzziness level for typo tolerance
            boost_exact: Whether to boost exact matches
            
        Returns:
            Tuple of (results, total_count)
        """
        if not self.client:
            self.connect()
        
        # Default fields with boosting
        if not fields:
            fields = settings.search.keyword.default_fields
        
        # Build query
        search_query = self._build_query(
            query=query,
            fields=fields,
            fuzziness=fuzziness,
            boost_exact=boost_exact,
            filters=filters
        )
        
        # Execute search
        try:
            response = self.client.search(
                index=self.index_name,
                body=search_query,
                size=limit,
                from_=offset
            )
            
            # Parse results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    'document_id': hit['_id'],
                    'score': hit['_score'],
                    **hit['_source']
                }
                results.append(result)
            
            total = response['hits']['total']['value']
            
            return results, total
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            raise
    
    def _build_query(
        self,
        query: str,
        fields: List[str],
        fuzziness: str,
        boost_exact: bool,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Elasticsearch query DSL."""
        # Multi-match query for fuzzy matching
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    "type": "best_fields",
                    "fuzziness": fuzziness,
                    "minimum_should_match": settings.search.keyword.minimum_should_match
                }
            }
        ]
        
        # Add exact match boost
        should_clauses = []
        if boost_exact:
            should_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": fields,
                    "type": "phrase",
                    "boost": 2.0
                }
            })
        
        # Build bool query
        bool_query = {
            "must": must_clauses,
            "should": should_clauses
        }
        
        # Add filters
        if filters:
            filter_clauses = self._build_filters(filters)
            if filter_clauses:
                bool_query["filter"] = filter_clauses
        
        return {
            "query": {
                "bool": bool_query
            }
        }
    
    def _build_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build filter clauses from filter dictionary."""
        filter_clauses = []
        
        # Code filter (FAM, PEN, CIV, etc.) - use exact keyword matching
        if code := filters.get("code.keyword"):
            filter_clauses.append({
                "term": {"code.keyword": code}
            })
        
        # Statute code exact match
        if statute_code := filters.get("statute_code"):
            filter_clauses.append({
                "term": {"statute_code": statute_code}
            })
        
        # Title contains
        if title_contains := filters.get("title_contains"):
            filter_clauses.append({
                "match": {"title": title_contains}
            })
        
        # Date range
        date_filter = {}
        if date_from := filters.get("date_from"):
            date_filter["gte"] = date_from
        if date_to := filters.get("date_to"):
            date_filter["lte"] = date_to
        
        if date_filter:
            filter_clauses.append({
                "range": {"effective_date": date_filter}
            })
        
        return filter_clauses
    
    def close(self) -> None:
        """Close Elasticsearch connection."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Closed Elasticsearch connection")

