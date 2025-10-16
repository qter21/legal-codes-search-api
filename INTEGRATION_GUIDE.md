# Integration Guide for codecond_ca Project

This guide explains how to integrate the Legal Codes Search API into your `codecond_ca` project.

## Prerequisites

1. Search API service running at a known URL (e.g., `http://localhost:8000`)
2. MongoDB contains section-level documents (one doc per section)
3. Data synced from MongoDB to Elasticsearch and Qdrant
4. API is healthy (check `/health` endpoint)

## Data Model

**Important**: The search API expects MongoDB to contain **section-level documents** with both content and architecture:

```json
{
  "statute_code": "CAL-CIVIL-1234",
  "title": "Section 1234 - Property Rights",
  "content": "Full section text...",
  "code_name": "Civil Code",
  
  // Code architecture (already in MongoDB)
  "division": "Division 1",
  "part": "Part 4", 
  "chapter": "Chapter 1"
}
```

**V1**: Search uses core fields only (statute_code, title, content, code_name)  
**V2**: Will add hierarchical navigation using existing architecture fields

**Search results return individual sections**, not entire codes. This provides:
- Precise citations (exact section numbers)
- Faster, more relevant results
- Better user experience (direct links to specific sections)

## Integration Steps

### 1. Install HTTP Client

Choose your preferred HTTP client library:

**Python:**
```bash
pip install httpx  # or requests
```

**JavaScript/TypeScript:**
```bash
npm install axios  # or fetch API
```

**Java:**
```xml
<!-- Add to pom.xml -->
<dependency>
    <groupId>com.squareup.okhttp3</groupId>
    <artifactId>okhttp</artifactId>
    <version>4.11.0</version>
</dependency>
```

### 2. Create Search Client

#### Python Example

```python
import httpx
from typing import List, Dict, Any, Optional

class LegalCodesSearchClient:
    """Client for Legal Codes Search API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
    
    def keyword_search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform keyword search."""
        response = self.client.post(
            "/search/keyword",
            json={
                "query": query,
                "limit": limit,
                "offset": offset,
                "filters": filters
            }
        )
        response.raise_for_status()
        return response.json()
    
    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Perform semantic search."""
        response = self.client.post(
            "/search/semantic",
            json={
                "query": query,
                "limit": limit,
                "score_threshold": score_threshold
            }
        )
        response.raise_for_status()
        return response.json()
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        fusion_method: str = "rrf"
    ) -> Dict[str, Any]:
        """Perform hybrid search (recommended)."""
        response = self.client.post(
            "/search/hybrid",
            json={
                "query": query,
                "limit": limit,
                "fusion_method": fusion_method
            }
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = self.client.get("/health")
        response.raise_for_status()
        return response.json()

# Usage
client = LegalCodesSearchClient("http://localhost:8000")

# Hybrid search (best for most use cases)
results = client.hybrid_search("property rights California")
for result in results["results"]:
    print(f"{result['statute_code']}: {result['title']} (score: {result['score']:.2f})")
```

#### JavaScript/TypeScript Example

```typescript
interface SearchResult {
  document_id: string;
  statute_code: string;
  title: string;
  section?: string;
  content?: string;
  score: number;
}

interface SearchResponse {
  success: boolean;
  results: SearchResult[];
  metadata: {
    total_results: number;
    returned_results: number;
    query_time_ms: number;
    search_type: string;
  };
}

class LegalCodesSearchClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  async keywordSearch(
    query: string,
    limit: number = 10,
    offset: number = 0
  ): Promise<SearchResponse> {
    const response = await fetch(`${this.baseUrl}/search/keyword`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit, offset }),
    });
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  async hybridSearch(
    query: string,
    limit: number = 10,
    fusionMethod: string = "rrf"
  ): Promise<SearchResponse> {
    const response = await fetch(`${this.baseUrl}/search/hybrid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit, fusion_method: fusionMethod }),
    });
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    
    return response.json();
  }

  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }
}

// Usage
const client = new LegalCodesSearchClient("http://localhost:8000");

const results = await client.hybridSearch("property rights");
results.results.forEach(result => {
  console.log(`${result.statute_code}: ${result.title} (${result.score.toFixed(2)})`);
});
```

### 3. Search Strategies

#### When to Use Keyword Search

Best for:
- Exact statute code lookups
- Specific legal terms and citations
- Known section numbers
- Precise phrase matching

```python
# Example: Find specific statute
results = client.keyword_search(
    query="Civil Code Section 1234",
    limit=5
)
```

#### When to Use Semantic Search

Best for:
- Conceptual queries
- Natural language questions
- Finding similar legal concepts
- Cross-referencing related statutes

```python
# Example: Find related concepts
results = client.semantic_search(
    query="What are the rights of property owners in California?",
    limit=10,
    score_threshold=0.75
)
```

#### When to Use Hybrid Search (Recommended)

Best for:
- General-purpose search
- Combining exact matching with semantic understanding
- Balancing precision and recall
- Most user-facing search interfaces

```python
# Example: Best of both worlds
results = client.hybrid_search(
    query="property rights",
    limit=10,
    fusion_method="rrf"  # Reciprocal Rank Fusion
)
```

### 4. Advanced Filtering

Apply filters to narrow down results:

```python
# Filter by statute code
results = client.hybrid_search(
    query="property",
    limit=10,
    filters={
        "statute_code": "CAL-CIVIL-1234"
    }
)

# Filter by date range
results = client.hybrid_search(
    query="new regulations",
    limit=10,
    filters={
        "date_from": "2023-01-01",
        "date_to": "2023-12-31"
    }
)

# Combine filters
results = client.hybrid_search(
    query="tenant rights",
    limit=10,
    filters={
        "title_contains": "residential",
        "date_from": "2020-01-01"
    }
)
```

### 5. Pagination

Implement pagination for large result sets:

```python
def paginated_search(query: str, page_size: int = 10):
    """Generator for paginated search results."""
    offset = 0
    while True:
        results = client.hybrid_search(
            query=query,
            limit=page_size,
            offset=offset
        )
        
        if not results["results"]:
            break
        
        yield results["results"]
        offset += page_size
        
        # Stop if we've retrieved all results
        if offset >= results["metadata"]["total_results"]:
            break

# Usage
for page in paginated_search("property rights", page_size=20):
    for result in page:
        print(result["title"])
```

### 6. Error Handling

Implement robust error handling:

```python
from httpx import HTTPStatusError, RequestError

def safe_search(query: str) -> Optional[Dict[str, Any]]:
    """Search with error handling."""
    try:
        results = client.hybrid_search(query)
        return results
    except HTTPStatusError as e:
        if e.response.status_code == 503:
            print("Search service temporarily unavailable")
        elif e.response.status_code == 400:
            print(f"Invalid query: {e.response.json()}")
        else:
            print(f"Search failed: {e}")
        return None
    except RequestError as e:
        print(f"Connection error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### 7. Caching Results

Cache frequently requested queries:

```python
from functools import lru_cache
import hashlib

class CachedSearchClient(LegalCodesSearchClient):
    """Search client with LRU caching."""
    
    @lru_cache(maxsize=1000)
    def _cached_hybrid_search(self, query_hash: str, limit: int):
        """Internal cached method."""
        return super().hybrid_search(query_hash, limit)
    
    def hybrid_search(self, query: str, limit: int = 10, **kwargs):
        """Hybrid search with caching."""
        # Create cache key from query
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return self._cached_hybrid_search(query_hash, limit)
```

## Best Practices

### 1. Use Hybrid Search by Default

For most use cases, hybrid search provides the best balance of precision and recall:

```python
# Default search implementation
def search_legal_codes(user_query: str):
    return client.hybrid_search(
        query=user_query,
        limit=20,
        fusion_method="rrf"
    )
```

### 2. Implement Timeout Handling

Set appropriate timeouts to prevent hanging requests:

```python
client = httpx.Client(
    base_url="http://localhost:8000",
    timeout=30.0  # 30 second timeout
)
```

### 3. Log Search Queries

Track search queries for analytics and improvement:

```python
import logging

logger = logging.getLogger(__name__)

def search_with_logging(query: str):
    logger.info(f"Search query: {query}")
    results = client.hybrid_search(query)
    logger.info(f"Results: {len(results['results'])} in {results['metadata']['query_time_ms']}ms")
    return results
```

### 4. Health Checks

Regularly check API health before searches:

```python
def ensure_api_healthy():
    """Check if search API is healthy."""
    try:
        health = client.health_check()
        return health["status"] == "healthy"
    except:
        return False
```

## Performance Optimization

### 1. Connection Pooling

Reuse HTTP connections:

```python
# Use a single client instance across your application
search_client = LegalCodesSearchClient("http://localhost:8000")
```

### 2. Batch Requests

If searching multiple queries, batch them:

```python
async def batch_search(queries: List[str]):
    """Search multiple queries concurrently."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.post("/search/hybrid", json={"query": q})
            for q in queries
        ]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

### 3. Result Limits

Request only what you need:

```python
# For autocomplete/suggestions
results = client.hybrid_search(query, limit=5)

# For full search results
results = client.hybrid_search(query, limit=20)
```

## Troubleshooting

### Connection Refused

```python
# Check if service is running
curl http://localhost:8000/health

# Check Docker containers
docker-compose ps
```

### Slow Queries

```python
# Monitor query times
print(f"Query took {results['metadata']['query_time_ms']}ms")

# Reduce limit if too slow
results = client.hybrid_search(query, limit=10)
```

### No Results

```python
# Try semantic search for broader matching
semantic_results = client.semantic_search(query, score_threshold=0.6)

# Check if data is synced
health = client.health_check()
print(f"Document count: {health['elasticsearch']['document_count']}")
```

## Support

For issues with the search API integration, contact [your team/support info].

