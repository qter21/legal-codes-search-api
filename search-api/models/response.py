"""Response models for search API."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Individual search result."""
    document_id: str = Field(..., description="Document ID")
    statute_code: str = Field(..., description="Statute code")
    title: str = Field(..., description="Document title")
    section: Optional[str] = Field(default=None, description="Section text")
    content: Optional[str] = Field(default=None, description="Content preview")
    effective_date: Optional[str] = Field(default=None, description="Effective date")
    score: float = Field(..., description="Relevance score")
    source: Optional[str] = Field(default=None, description="Result source: keyword, semantic, or hybrid")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "507f1f77bcf86cd799439011",
                "statute_code": "CAL-CIVIL-1234",
                "title": "Civil Code Section 1234",
                "section": "Section 1234",
                "content": "This section defines...",
                "effective_date": "2023-01-01",
                "score": 0.95,
                "source": "hybrid"
            }
        }


class SearchMetadata(BaseModel):
    """Search metadata."""
    total_results: int = Field(..., description="Total number of results")
    returned_results: int = Field(..., description="Number of results in this response")
    offset: int = Field(..., description="Result offset")
    limit: int = Field(..., description="Result limit")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")
    search_type: str = Field(..., description="Type of search: keyword, semantic, or hybrid")


class SearchResponse(BaseModel):
    """Search response."""
    success: bool = Field(default=True, description="Whether the search was successful")
    results: List[SearchResult] = Field(default=[], description="Search results")
    metadata: SearchMetadata = Field(..., description="Search metadata")
    message: Optional[str] = Field(default=None, description="Optional message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "results": [
                    {
                        "document_id": "507f1f77bcf86cd799439011",
                        "statute_code": "CAL-CIVIL-1234",
                        "title": "Civil Code Section 1234",
                        "section": "Section 1234",
                        "content": "This section defines...",
                        "effective_date": "2023-01-01",
                        "score": 0.95,
                        "source": "hybrid"
                    }
                ],
                "metadata": {
                    "total_results": 100,
                    "returned_results": 10,
                    "offset": 0,
                    "limit": 10,
                    "query_time_ms": 45.2,
                    "search_type": "hybrid"
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Invalid search query",
                "details": {"field": "query", "reason": "Query cannot be empty"}
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    elasticsearch: Dict[str, Any] = Field(..., description="Elasticsearch status")
    qdrant: Dict[str, Any] = Field(..., description="Qdrant status")
    embedding_model: Dict[str, Any] = Field(..., description="Embedding model status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "elasticsearch": {
                    "connected": True,
                    "index": "legal_codes",
                    "document_count": 150000
                },
                "qdrant": {
                    "connected": True,
                    "collection": "legal_codes_vectors",
                    "point_count": 150000
                },
                "embedding_model": {
                    "loaded": True,
                    "model": "all-MiniLM-L6-v2",
                    "dimension": 384
                }
            }
        }

