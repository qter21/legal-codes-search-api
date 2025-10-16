"""Request models for search API."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class SearchRequest(BaseModel):
    """Base search request."""
    query: str = Field(..., description="Search query text", min_length=1)
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)
    offset: int = Field(default=0, description="Number of results to skip", ge=0)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")
    
    @validator('query')
    def query_not_empty(cls, v):
        """Validate query is not empty after stripping."""
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class KeywordSearchRequest(SearchRequest):
    """Keyword search request."""
    fields: Optional[List[str]] = Field(
        default=None,
        description="Fields to search in (defaults to title, section, content)"
    )
    code_filter: Optional[str] = Field(
        default=None,
        description="Filter by legal code (e.g., FAM, PEN, CIV)"
    )
    fuzziness: Optional[str] = Field(
        default="AUTO",
        description="Fuzziness level for typo tolerance"
    )
    boost_exact_matches: bool = Field(
        default=True,
        description="Boost exact phrase matches"
    )


class SemanticSearchRequest(SearchRequest):
    """Semantic search request."""
    score_threshold: Optional[float] = Field(
        default=0.7,
        description="Minimum similarity score",
        ge=0.0,
        le=1.0
    )
    include_scores: bool = Field(
        default=True,
        description="Include similarity scores in response"
    )


class HybridSearchRequest(SearchRequest):
    """Hybrid search request combining keyword and semantic search."""
    keyword_weight: Optional[float] = Field(
        default=0.5,
        description="Weight for keyword search results",
        ge=0.0,
        le=1.0
    )
    semantic_weight: Optional[float] = Field(
        default=0.5,
        description="Weight for semantic search results",
        ge=0.0,
        le=1.0
    )
    fusion_method: Optional[str] = Field(
        default="rrf",
        description="Result fusion method: 'rrf' or 'weighted'"
    )
    
    @validator('semantic_weight')
    def validate_weights(cls, v, values):
        """Ensure weights sum to 1.0 for weighted fusion."""
        if 'keyword_weight' in values:
            kw_weight = values['keyword_weight']
            if values.get('fusion_method') == 'weighted':
                total = kw_weight + v
                if abs(total - 1.0) > 0.01:  # Allow small floating point errors
                    raise ValueError('Weights must sum to 1.0 for weighted fusion')
        return v


class FilterRequest(BaseModel):
    """Filter criteria for search."""
    statute_code: Optional[str] = Field(default=None, description="Exact statute code")
    title_contains: Optional[str] = Field(default=None, description="Title contains text")
    date_from: Optional[str] = Field(default=None, description="Effective date from (YYYY-MM-DD)")
    date_to: Optional[str] = Field(default=None, description="Effective date to (YYYY-MM-DD)")

