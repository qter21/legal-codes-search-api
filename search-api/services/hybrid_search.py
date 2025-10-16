"""Hybrid search service combining keyword and semantic search."""
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

from config import settings
from services.elasticsearch_service import ElasticsearchService
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService


class HybridSearchService:
    """Service for hybrid search combining keyword and semantic results."""
    
    def __init__(
        self,
        es_service: ElasticsearchService,
        qdrant_service: QdrantService,
        embedding_service: EmbeddingService
    ):
        """Initialize hybrid search service."""
        self.es_service = es_service
        self.qdrant_service = qdrant_service
        self.embedding_service = embedding_service
    
    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
        fusion_method: str = "rrf"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Perform hybrid search combining keyword and semantic results.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Optional filters
            keyword_weight: Weight for keyword results (for weighted fusion)
            semantic_weight: Weight for semantic results (for weighted fusion)
            fusion_method: Result fusion method ('rrf' or 'weighted')
            
        Returns:
            Tuple of (results, estimated_total)
        """
        # Retrieve top N from each source
        retrieve_n = settings.search.hybrid.retrieve_top_n
        
        # Perform keyword search
        logger.debug(f"Performing keyword search for: {query}")
        keyword_results, keyword_total = self.es_service.search(
            query=query,
            limit=retrieve_n,
            offset=0,
            filters=filters
        )
        
        # Perform semantic search
        logger.debug(f"Generating embedding for query: {query}")
        query_vector = self.embedding_service.encode(query)
        
        logger.debug(f"Performing semantic search")
        semantic_results = self.qdrant_service.search(
            query_vector=query_vector,
            limit=retrieve_n,
            offset=0,
            filters=filters
        )
        
        # Fuse results
        if fusion_method == "rrf":
            fused_results = self._reciprocal_rank_fusion(
                keyword_results,
                semantic_results,
                k=settings.search.hybrid.rrf_k
            )
        else:  # weighted
            fused_results = self._weighted_fusion(
                keyword_results,
                semantic_results,
                keyword_weight,
                semantic_weight
            )
        
        # Apply offset and limit
        total_results = len(fused_results)
        fused_results = fused_results[offset:offset + limit]
        
        # Mark source as hybrid
        for result in fused_results:
            result['source'] = 'hybrid'
        
        return fused_results, total_results
    
    def _reciprocal_rank_fusion(
        self,
        keyword_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fuse results using Reciprocal Rank Fusion (RRF).
        
        RRF Score = sum(1 / (k + rank_i)) for each result list
        
        Args:
            keyword_results: Results from keyword search
            semantic_results: Results from semantic search
            k: RRF constant (typically 60)
            
        Returns:
            Fused and sorted results
        """
        # Build document scores
        doc_scores = {}
        doc_data = {}
        
        # Add keyword results
        for rank, result in enumerate(keyword_results, start=1):
            doc_id = result['document_id']
            score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score
            if doc_id not in doc_data:
                doc_data[doc_id] = result
        
        # Add semantic results
        for rank, result in enumerate(semantic_results, start=1):
            doc_id = result['document_id']
            score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score
            if doc_id not in doc_data:
                doc_data[doc_id] = result
        
        # Sort by fused score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build result list
        results = []
        for doc_id, score in sorted_docs:
            result = doc_data[doc_id].copy()
            result['score'] = score
            results.append(result)
        
        return results
    
    def _weighted_fusion(
        self,
        keyword_results: List[Dict[str, Any]],
        semantic_results: List[Dict[str, Any]],
        keyword_weight: float,
        semantic_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Fuse results using weighted score combination.
        
        Args:
            keyword_results: Results from keyword search
            semantic_results: Results from semantic search
            keyword_weight: Weight for keyword scores
            semantic_weight: Weight for semantic scores
            
        Returns:
            Fused and sorted results
        """
        # Normalize scores to [0, 1] range
        keyword_results = self._normalize_scores(keyword_results)
        semantic_results = self._normalize_scores(semantic_results)
        
        # Build document scores
        doc_scores = {}
        doc_data = {}
        
        # Add keyword results
        for result in keyword_results:
            doc_id = result['document_id']
            score = result['score'] * keyword_weight
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score
            if doc_id not in doc_data:
                doc_data[doc_id] = result
        
        # Add semantic results
        for result in semantic_results:
            doc_id = result['document_id']
            score = result['score'] * semantic_weight
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score
            if doc_id not in doc_data:
                doc_data[doc_id] = result
        
        # Sort by fused score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build result list
        results = []
        for doc_id, score in sorted_docs:
            result = doc_data[doc_id].copy()
            result['score'] = score
            results.append(result)
        
        return results
    
    def _normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize scores to [0, 1] range using min-max normalization."""
        if not results:
            return results
        
        scores = [r['score'] for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            # All scores are the same
            for result in results:
                result['score'] = 1.0
        else:
            # Min-max normalization
            for result in results:
                result['score'] = (result['score'] - min_score) / (max_score - min_score)
        
        return results

