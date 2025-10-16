"""Search API router."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
import time

from models.request import (
    KeywordSearchRequest,
    SemanticSearchRequest,
    HybridSearchRequest
)
from models.response import (
    SearchResponse,
    SearchResult,
    SearchMetadata,
    ErrorResponse
)
from services.elasticsearch_service import ElasticsearchService
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService
from services.hybrid_search import HybridSearchService


router = APIRouter(prefix="/search", tags=["search"])

# Service instances (will be initialized in main.py)
es_service: Optional[ElasticsearchService] = None
qdrant_service: Optional[QdrantService] = None
embedding_service: Optional[EmbeddingService] = None
hybrid_search_service: Optional[HybridSearchService] = None


def get_services():
    """Dependency to ensure services are initialized."""
    if not all([es_service, qdrant_service, embedding_service, hybrid_search_service]):
        raise HTTPException(
            status_code=503,
            detail="Services not initialized"
        )
    return {
        "es": es_service,
        "qdrant": qdrant_service,
        "embedding": embedding_service,
        "hybrid": hybrid_search_service
    }


@router.post("/keyword", response_model=SearchResponse)
async def keyword_search(
    request: KeywordSearchRequest,
    services: dict = Depends(get_services)
) -> SearchResponse:
    """
    Perform keyword-based search using Elasticsearch.
    
    This endpoint uses traditional full-text search with BM25 ranking,
    fuzzy matching, and field boosting for relevance.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Keyword search: {request.query}")
        
        # Add code filter if specified
        filters = request.filters or {}
        if request.code_filter:
            filters["code.keyword"] = request.code_filter
        
        # Perform search
        results, total = services["es"].search(
            query=request.query,
            limit=request.limit,
            offset=request.offset,
            fields=request.fields,
            filters=filters,
            fuzziness=request.fuzziness,
            boost_exact=request.boost_exact_matches
        )
        
        # Convert to response format
        search_results = [
            SearchResult(
                document_id=r['document_id'],
                statute_code=r.get('code', '') or r.get('statute_code', ''),  # Use 'code' field (FAM, PEN, etc.)
                title=r.get('title', ''),
                section=r.get('section'),
                content=r.get('content', '')[:500] if r.get('content') else None,  # Preview
                effective_date=str(r.get('effective_date')) if r.get('effective_date') else None,
                score=r['score'],
                source='keyword'
            )
            for r in results
        ]
        
        query_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            success=True,
            results=search_results,
            metadata=SearchMetadata(
                total_results=total,
                returned_results=len(search_results),
                offset=request.offset,
                limit=request.limit,
                query_time_ms=query_time,
                search_type='keyword'
            )
        )
        
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    services: dict = Depends(get_services)
) -> SearchResponse:
    """
    Perform semantic search using vector embeddings and Qdrant.
    
    This endpoint converts the query to a vector embedding and finds
    similar documents based on cosine similarity.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Semantic search: {request.query}")
        
        # Generate query embedding
        query_vector = services["embedding"].encode(request.query)
        
        # Perform search
        results = services["qdrant"].search(
            query_vector=query_vector,
            limit=request.limit,
            offset=request.offset,
            filters=request.filters,
            score_threshold=request.score_threshold
        )
        
        # Convert to response format
        search_results = [
            SearchResult(
                document_id=r['document_id'],
                statute_code=r.get('statute_code', ''),
                title=r.get('title', ''),
                section=r.get('section'),
                content=None,  # Qdrant doesn't store full content
                effective_date=r.get('effective_date'),
                score=r['score'],
                source='semantic'
            )
            for r in results
        ]
        
        query_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            success=True,
            results=search_results,
            metadata=SearchMetadata(
                total_results=len(results),  # Qdrant doesn't return total
                returned_results=len(search_results),
                offset=request.offset,
                limit=request.limit,
                query_time_ms=query_time,
                search_type='semantic'
            )
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    services: dict = Depends(get_services)
) -> SearchResponse:
    """
    Perform hybrid search combining keyword and semantic search.
    
    This endpoint combines results from both Elasticsearch (keyword)
    and Qdrant (semantic) using Reciprocal Rank Fusion (RRF) or
    weighted score combination.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Hybrid search: {request.query} (fusion: {request.fusion_method})")
        
        # Perform hybrid search
        results, total = services["hybrid"].search(
            query=request.query,
            limit=request.limit,
            offset=request.offset,
            filters=request.filters,
            keyword_weight=request.keyword_weight,
            semantic_weight=request.semantic_weight,
            fusion_method=request.fusion_method
        )
        
        # Convert to response format
        search_results = [
            SearchResult(
                document_id=r['document_id'],
                statute_code=r.get('statute_code', ''),
                title=r.get('title', ''),
                section=r.get('section'),
                content=r.get('content', '')[:500] if r.get('content') else None,
                effective_date=str(r.get('effective_date')) if r.get('effective_date') else None,
                score=r['score'],
                source=r.get('source', 'hybrid')
            )
            for r in results
        ]
        
        query_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            success=True,
            results=search_results,
            metadata=SearchMetadata(
                total_results=total,
                returned_results=len(search_results),
                offset=request.offset,
                limit=request.limit,
                query_time_ms=query_time,
                search_type='hybrid'
            )
        )
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

