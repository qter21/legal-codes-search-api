# Legal Codes Search Architecture Design

## Architecture Overview

A hybrid search system combining Elasticsearch (keyword/text search) and Qdrant (semantic vector search) with MongoDB as the source of truth, serving the codecond_ca project.

## System Components

### 1. Data Layer

- **MongoDB**: Source of truth for CA legal codes data (existing pipeline storage)
- **Elasticsearch**: Text search engine for traditional keyword/fuzzy/statute search
- **Qdrant**: Vector database for semantic similarity search

### 2. Data Sync Pipeline Service

A scheduled batch job that synchronizes data from MongoDB to both search engines:

**Key responsibilities:**

- Read documents from MongoDB (in batches)
- Generate embeddings using self-hosted model
- Index to Elasticsearch (text fields)
- Index to Qdrant (vectors + metadata)
- Track sync state (last sync timestamp, failed documents)

**Implementation approach:**

```
sync-service/
├── models/
│   └── embedding_model.py      # Self-hosted embedding model wrapper
├── extractors/
│   └── mongodb_extractor.py    # Fetch data from MongoDB
├── indexers/
│   ├── elasticsearch_indexer.py
│   └── qdrant_indexer.py
├── sync_job.py                 # Main batch sync orchestrator
└── config.py                   # Connection configs
```

### 3. Search API Service

FastAPI/Flask service that coordinates searches across both engines:

**Core endpoints:**

- `POST /search/keyword` - Pure Elasticsearch search
- `POST /search/semantic` - Pure Qdrant vector search  
- `POST /search/hybrid` - Combined results with configurable weighting

**Search flow:**

1. Receive query from codecond_ca project
2. For hybrid search:
   - Query Elasticsearch for keyword matches
   - Generate query embedding and search Qdrant
   - Merge and rank results using RRF (Reciprocal Rank Fusion)
3. Return unified response with relevance scores

**API structure:**

```
search-api/
├── routers/
│   └── search.py               # Search endpoints
├── services/
│   ├── elasticsearch_service.py
│   ├── qdrant_service.py
│   └── hybrid_search.py        # Result merging logic
├── models/
│   ├── request.py              # Search request schemas
│   └── response.py             # Unified response format
└── main.py
```

### 4. Embedding Model Service

Self-hosted embedding generation (sentence-transformers):

**Options:**

- `all-MiniLM-L6-v2`: Fast, lightweight (80MB)
- `legal-bert-base`: Domain-specific for legal text
- Deploy via FastAPI endpoint or direct Python library

## Data Schema Design

### MongoDB Document (Section-Level)

**Important**: Each MongoDB document represents **one section** of a legal code (not an entire code). For California codes with 1,000-20,000 sections each, this provides optimal granularity for search and retrieval.

MongoDB contains both **section contents** and **code architecture** (hierarchical structure):

```json
{
  "_id": "...",
  "statute_code": "CAL-CIVIL-1234",        // Unique section identifier
  "title": "Section 1234 - Property Rights",
  "section": "Section 1234",               // Section number
  "content": "Full text of this section...", // Section content
  
  // Code architecture (hierarchical structure)
  "code_name": "Civil Code",               // Which code this belongs to
  "division": "Division 1",                // Already in MongoDB
  "part": "Part 4",                        // Already in MongoDB
  "chapter": "Chapter 1",                  // Already in MongoDB
  "title_level": "Title 2",                // Already in MongoDB (if exists)
  
  "effective_date": "2023-01-01",
  "updated_at": "2023-06-15"
}
```

**V1 Design**: Use **flat fields only** (statute_code, title, content, code_name) for simplicity and faster delivery. The sync service extracts just these fields.

**V2 Enhancements** (future): Leverage the **existing hierarchical fields** (division, part, chapter) for advanced navigation, filtering, and cross-reference following. No MongoDB schema changes needed!

### Elasticsearch Index Mapping

```json
{
  "mappings": {
    "properties": {
      "statute_code": {"type": "keyword"},
      "title": {"type": "text", "analyzer": "legal_text_analyzer"},
      "section": {"type": "text", "analyzer": "legal_text_analyzer"},
      "content": {"type": "text", "analyzer": "legal_text_analyzer"},
      "code_name": {"type": "keyword"},
      "effective_date": {"type": "date"},
      "updated_at": {"type": "date"},
      "document_id": {"type": "keyword"}
    }
  }
}
```

**Note**: Each indexed document represents one section. For 20,000 CA code sections, this creates 20,000 search documents - well within the medium scale target (100K-1M).

### Qdrant Collection Schema

- **Vector dimension**: 384 (MiniLM) or 768 (BERT)
- **Distance metric**: Cosine similarity
- **Payload**: statute_code, title, section, code_name (for filtering and display)
- **Index**: HNSW for fast approximate search
- **Granularity**: One vector per section (optimal for legal code search)

**Embedding Strategy**: Combine section title and content to create rich semantic representation while preserving section-level precision.

## Deployment Architecture

```
┌─────────────────┐
│   codecond_ca   │ (Client)
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Search API     │ (FastAPI)
│  Service        │
└────┬───────┬────┘
     │       │
     │       └──────────┐
     ▼                  ▼
┌──────────────┐  ┌──────────────┐
│Elasticsearch │  │   Qdrant     │
│   (Port      │  │   (Port      │
│    9200)     │  │    6333)     │
└──────────────┘  └──────────────┘
     ▲                  ▲
     │                  │
     └────────┬─────────┘
              │
     ┌────────┴────────┐
     │  Sync Service   │ (Scheduled)
     │  + Embedding    │
     └────────┬────────┘
              │
              ▼
     ┌────────────────┐
     │    MongoDB     │ (Source of Truth)
     └────────────────┘
```

## Technology Stack

- **Search API**: FastAPI + Python 3.11+
- **Elasticsearch**: v8.x (latest stable)
- **Qdrant**: v1.7+ (Docker deployment)
- **Embedding Model**: sentence-transformers (HuggingFace)
- **MongoDB Driver**: motor (async) or pymongo
- **Scheduling**: APScheduler or Kubernetes CronJob
- **Containerization**: Docker Compose for local dev

## Implementation Phases

### Phase 1: Core Infrastructure Setup

- Set up Elasticsearch cluster/instance
- Deploy Qdrant vector database
- Configure MongoDB connection
- Create Docker Compose for local development

### Phase 2: Embedding Model Integration

- Select and test embedding model (legal-bert vs MiniLM)
- Create embedding generation service
- Benchmark embedding performance on sample legal text

### Phase 3: Data Sync Pipeline

- Implement MongoDB extractor with batch processing
- Build Elasticsearch indexer with proper mappings
- Build Qdrant indexer with vector storage
- Add error handling and retry logic
- Create sync status tracking

### Phase 4: Search API Development

- Implement keyword search endpoint (Elasticsearch)
- Implement semantic search endpoint (Qdrant)
- Build hybrid search with result fusion (RRF algorithm)
- Add filtering, pagination, and sorting
- Implement caching layer (Redis optional)

### Phase 5: Testing & Optimization

- Load test with medium-scale dataset (100K-1M docs)
- Tune Elasticsearch analyzers for legal text
- Optimize Qdrant HNSW parameters
- Benchmark query latency (target: <100ms p95)
- A/B test different embedding models

### Phase 6: Production Deployment

- Set up monitoring (Prometheus + Grafana)
- Configure backup strategies
- Deploy sync job scheduler
- API documentation (OpenAPI/Swagger)
- Integration guide for codecond_ca project

## Configuration Files to Create

1. **docker-compose.yml**: All services for local dev
2. **elasticsearch-mapping.json**: Index configuration
3. **qdrant-config.yaml**: Collection settings
4. **sync-config.yaml**: Batch sizes, schedules, MongoDB queries
5. **api-config.yaml**: Service endpoints, timeouts, weights for hybrid search

## Key Design Decisions

**Why Elasticsearch + Qdrant over ES alone?**

- Qdrant specializes in vector search with better performance
- Separate scaling: text search vs vector workloads
- Easier to swap embedding models without re-indexing text data

**Batch sync vs real-time?**

- Legal codes update infrequently (daily/weekly acceptable)
- Simpler implementation without MongoDB change streams
- Lower operational complexity

**Self-hosted embeddings?**

- Cost-effective for medium scale
- No external API dependencies
- Data privacy for legal documents

**Section-level chunking?**

- **V1 Approach**: One MongoDB document = One section = One search result
- Natural semantic boundaries (sections are complete legal concepts)
- Optimal granularity: Sections typically 100-500 words (fits embedding models)
- Precise citations: Results point to exact sections
- Scalable: 20,000 CA sections → 20,000 search docs (very manageable)
- **V2 Future**: Add hierarchical navigation (division/part/chapter) and cross-references

## Performance Targets

- **Indexing throughput**: 1K docs/minute
- **Search latency**: <100ms (p95)
- **Hybrid search**: <200ms (p95)
- **Sync job**: Complete in <2 hours for full dataset

