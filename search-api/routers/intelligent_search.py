"""Intelligent search router with query classification and RAG."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
from loguru import logger

from models.request import SearchRequest
from models.response import SearchResponse, SearchResult, SearchMetadata
from services.query_classifier import QueryClassifier
from services.rag_service import RAGService

router = APIRouter(prefix="/intelligent", tags=["intelligent-search"])

# Initialize classifier
query_classifier = QueryClassifier()


# Import services from main module at runtime to avoid circular imports
def get_services():
    """Get service instances from main module."""
    from main import es_service, qdrant_service, embedding_service, hybrid_search_service, llm_service
    return {
        "es": es_service,
        "qdrant": qdrant_service,
        "embedding": embedding_service,
        "hybrid": hybrid_search_service,
        "llm": llm_service  # May be None if not available
    }


class IntelligentSearchRequest(BaseModel):
    """Request for intelligent search with automatic routing."""
    query: str = Field(..., description="User query", min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")
    force_mode: Optional[str] = Field(
        default=None,
        description="Force search mode: 'simple' or 'complex' (overrides classification)"
    )


class IntelligentSearchResponse(BaseModel):
    """Response from intelligent search."""
    query: str
    classification: str  # 'simple' or 'complex'
    classification_reason: str
    search_mode: str  # 'keyword', 'hybrid', or 'rag'
    results: List[SearchResult]
    metadata: SearchMetadata
    rag_context: Optional[Dict[str, Any]] = None


@router.post("/search", response_model=IntelligentSearchResponse)
async def intelligent_search(
    request: IntelligentSearchRequest,
    services: dict = Depends(get_services)
) -> IntelligentSearchResponse:
    """
    Intelligent search that automatically routes queries:
    - Simple queries (code/section lookups) → Fast keyword search
    - Complex queries (semantic questions) → RAG with LLM
    
    Examples:
    - Simple: "FAM 3044", "Family Code Section 3044", "Section 3044"
    - Complex: "What are parental rights after divorce?", "How does custody work?"
    """
    start_time = time.time()
    
    try:
        logger.info(f"Intelligent search: {request.query}")
        
        # Step 1: Classify query
        if request.force_mode:
            classification = request.force_mode
            metadata_dict = {'forced': True, 'reason': f'User forced {request.force_mode} mode'}
        else:
            classification, metadata_dict = query_classifier.classify(request.query)
        
        # Step 2: Route to appropriate search method
        if classification == 'simple':
            # Simple query → Fast keyword search
            search_mode = 'keyword'
            
            # Extract code filter if present
            code_filter = query_classifier.extract_code_filter(request.query)
            
            # Perform keyword search
            filters = {}
            if code_filter:
                filters["code.keyword"] = code_filter
            
            results, total = services["es"].search(
                query=request.query,
                limit=request.limit,
                filters=filters,
                fuzziness="AUTO",
                boost_exact=True
            )
            
            # Convert to response format
            search_results = [
                SearchResult(
                    document_id=r['document_id'],
                    statute_code=r.get('code', '') or r.get('statute_code', ''),
                    title=r.get('title', ''),
                    section=r.get('section'),
                    content=r.get('content', '')[:500] if r.get('content') else None,
                    effective_date=str(r.get('effective_date')) if r.get('effective_date') else None,
                    score=r['score'],
                    source='keyword'
                )
                for r in results
            ]
            
            rag_context = None
            
        else:
            # Complex query → RAG with semantic search
            search_mode = 'rag'
            
            # Initialize RAG service with LLM if available
            llm_service = services.get("llm")  # Optional LLM service
            rag_service = RAGService(
                es_service=services["es"],
                qdrant_service=services["qdrant"],
                embedding_model=services["embedding"],
                llm_service=llm_service
            )
            
            # Perform RAG query
            rag_response = rag_service.answer_query(
                query=request.query,
                top_k=request.limit,
                context_limit=5
            )
            
            # Convert to response format
            search_results = [
                SearchResult(
                    document_id=r.get('document_id', ''),
                    statute_code=r.get('code', '') or r.get('statute_code', ''),
                    title=r.get('title', ''),
                    section=r.get('section'),
                    content=r.get('content', '')[:500] if r.get('content') else None,
                    effective_date=str(r.get('effective_date')) if r.get('effective_date') else None,
                    score=r.get('score', r.get('relevance_score', 0)),
                    source='rag'
                )
                for r in rag_response['all_results']
            ]
            
            total = len(search_results)
            rag_context = {
                'summary': rag_response['summary'],
                'relevant_sections': rag_response['relevant_sections'],
                'context_used': rag_response['context_used']
            }
        
        # Build response
        query_time = (time.time() - start_time) * 1000
        
        return IntelligentSearchResponse(
            query=request.query,
            classification=classification,
            classification_reason=metadata_dict.get('reason', ''),
            search_mode=search_mode,
            results=search_results,
            metadata=SearchMetadata(
                total_results=len(search_results),
                returned_results=len(search_results),
                query_time_ms=query_time,
                page=1,
                page_size=request.limit,
                offset=0,
                limit=request.limit,
                search_type=search_mode
            ),
            rag_context=rag_context
        )
        
    except Exception as e:
        logger.error(f"Error in intelligent search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classify", response_model=Dict[str, Any])
async def classify_query(query: str) -> Dict[str, Any]:
    """
    Classify a query without performing search.
    Useful for debugging and understanding query routing.
    
    Example: GET /intelligent/classify?query=FAM+3044
    """
    classification, metadata = query_classifier.classify(query)
    
    return {
        "query": query,
        "classification": classification,
        "metadata": metadata,
        "recommended_search_mode": "keyword" if classification == "simple" else "rag"
    }

