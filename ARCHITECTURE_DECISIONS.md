# Architecture Decision Records (ADR)

This document records the key architectural decisions made for the Legal Codes Search system.

## ADR-001: Hybrid Search Architecture (Elasticsearch + Qdrant)

**Status**: Accepted

**Context**: 
We need to provide both traditional keyword search and semantic search capabilities for legal codes. Legal professionals need exact statute lookups but also benefit from conceptual similarity search.

**Decision**: 
Use a hybrid architecture combining Elasticsearch for keyword search and Qdrant for semantic vector search, rather than using Elasticsearch alone (which has vector search since v8.0).

**Rationale**:
1. **Specialization**: Qdrant is purpose-built for vector search with better performance and features
2. **Independent Scaling**: Can scale text and vector workloads separately
3. **Flexibility**: Easier to swap embedding models without re-indexing text data
4. **Best-of-Breed**: Elasticsearch excels at text search, Qdrant at vector search
5. **Future-Proof**: Can upgrade either component independently

**Consequences**:
- **Positive**: Better performance for both search types, flexible scaling
- **Negative**: Increased operational complexity, more services to maintain
- **Neutral**: Two sync paths instead of one

**Alternatives Considered**:
1. Elasticsearch only with vector support (rejected: less optimized for vectors)
2. Qdrant only (rejected: weaker text search capabilities)
3. Separate PostgreSQL with pgvector (rejected: more complex, slower)

---

## ADR-002: Batch Sync vs Real-time Sync

**Status**: Accepted

**Context**: 
Need to synchronize legal codes data from MongoDB to search engines. Legal codes are updated infrequently (weekly/monthly).

**Decision**: 
Implement batch synchronization with scheduled jobs rather than real-time sync using MongoDB change streams.

**Rationale**:
1. **Update Frequency**: Legal codes change infrequently, real-time not required
2. **Simplicity**: Batch jobs are simpler to implement and debug
3. **Resource Efficiency**: No continuous connection overhead
4. **Reliability**: Easier error handling and retry logic
5. **Operational Simplicity**: Standard cron-based scheduling

**Consequences**:
- **Positive**: Simpler implementation, lower resource usage, easier maintenance
- **Negative**: Data is eventually consistent (acceptable for this use case)
- **Neutral**: Daily sync window is acceptable for legal codes

**Alternatives Considered**:
1. MongoDB Change Streams (rejected: unnecessary complexity for update frequency)
2. Manual sync (rejected: error-prone, requires manual intervention)
3. Event-driven with Kafka (rejected: over-engineering for scale)

---

## ADR-003: Self-hosted Embeddings

**Status**: Accepted

**Context**: 
Need to generate embeddings for semantic search. Must consider cost, latency, privacy, and scalability.

**Decision**: 
Use self-hosted sentence-transformers models instead of external embedding APIs (OpenAI, Cohere, etc.).

**Rationale**:
1. **Cost**: No per-request API costs, predictable infrastructure costs
2. **Privacy**: Legal documents stay internal, no data sent to third parties
3. **Latency**: Local inference eliminates API round-trip
4. **Scale**: Can process large batches efficiently
5. **Control**: Can fine-tune models on legal text if needed

**Consequences**:
- **Positive**: Cost-effective at scale, data privacy, consistent latency
- **Negative**: Need to host and manage embedding model, some quality trade-off vs GPT embeddings
- **Neutral**: Requires GPU for optimal performance in production

**Alternatives Considered**:
1. OpenAI Embeddings (rejected: cost at scale, data privacy concerns)
2. Cohere Embeddings (rejected: similar cost and privacy issues)
3. AWS SageMaker (rejected: vendor lock-in, higher cost)

**Model Selection**:
- Primary: `all-MiniLM-L6-v2` (384-dim, fast, good quality)
- Alternative: `legal-bert-base-uncased` (768-dim, domain-specific)

---

## ADR-004: Reciprocal Rank Fusion (RRF) for Hybrid Search

**Status**: Accepted

**Context**: 
Need to combine results from keyword and semantic search into a single ranked list.

**Decision**: 
Use Reciprocal Rank Fusion (RRF) as the primary fusion method, with weighted combination as an alternative.

**Rationale**:
1. **Parameter-Free**: RRF doesn't require tuning weights
2. **Proven**: Well-established algorithm in information retrieval
3. **Robust**: Works well across different query types
4. **Fair**: Balances contributions from both search methods
5. **Simple**: Easy to implement and understand

**Formula**: `RRF_score(d) = Σ(1 / (k + rank_i))` where k=60 (standard)

**Consequences**:
- **Positive**: Good results without tuning, robust across queries
- **Negative**: Less control than weighted combination
- **Neutral**: Can still offer weighted fusion as an option

**Alternatives Considered**:
1. Weighted Score Combination (kept as alternative: allows fine-tuning)
2. Linear Combination (rejected: requires score normalization)
3. Learn-to-Rank (rejected: requires training data and complexity)

---

## ADR-005: FastAPI for Search API

**Status**: Accepted

**Context**: 
Need a web framework for the search API service.

**Decision**: 
Use FastAPI instead of Flask or other Python web frameworks.

**Rationale**:
1. **Performance**: ASGI-based, async support for concurrent requests
2. **Type Safety**: Pydantic models for request/response validation
3. **Documentation**: Auto-generated OpenAPI/Swagger docs
4. **Modern**: Python 3.11+ with type hints
5. **Developer Experience**: Excellent tooling and IDE support

**Consequences**:
- **Positive**: Fast development, type safety, excellent docs, good performance
- **Negative**: Team needs to learn async Python if unfamiliar
- **Neutral**: Requires Python 3.11+

**Alternatives Considered**:
1. Flask (rejected: synchronous, less type safety)
2. Django REST Framework (rejected: heavyweight for this use case)
3. Node.js/Express (rejected: different language, team expertise)

---

## ADR-006: MongoDB as Source of Truth

**Status**: Accepted

**Context**: 
The data pipeline project stores CA codes in MongoDB. Need to decide if search engines should be primary storage or derived.

**Decision**: 
Keep MongoDB as the source of truth. Elasticsearch and Qdrant are derived indexes optimized for search.

**Rationale**:
1. **Existing System**: MongoDB already in use, no need to change
2. **Separation of Concerns**: Data storage vs search optimization
3. **Flexibility**: Can rebuild search indexes without losing data
4. **Single Source**: Clear authority for canonical data
5. **Data Integrity**: MongoDB provides ACID transactions

**Consequences**:
- **Positive**: Clear data ownership, can rebuild indexes, existing workflows intact
- **Negative**: Data duplication across systems, sync required
- **Neutral**: MongoDB not optimized for search, but not needed for that

**Alternatives Considered**:
1. Elasticsearch as primary (rejected: not designed as primary database)
2. Dual writes to MongoDB and search engines (rejected: consistency issues)

---

## ADR-007: Stateless API Design

**Status**: Accepted

**Context**: 
Need to design API for horizontal scalability.

**Decision**: 
Design the search API as a stateless service with no session storage or in-memory state.

**Rationale**:
1. **Scalability**: Can add/remove API instances freely
2. **Load Balancing**: Any request can go to any instance
3. **Resilience**: Instance failures don't affect other requests
4. **Simplicity**: No state synchronization needed
5. **Cloud-Native**: Fits container orchestration patterns

**Consequences**:
- **Positive**: Easy horizontal scaling, simple deployment
- **Negative**: Query caching requires external store (Redis)
- **Neutral**: Embedding model loaded in each instance (can optimize with shared model server)

**Alternatives Considered**:
1. Sticky sessions (rejected: complicates load balancing)
2. Shared state with Redis (kept for optional query caching)

---

## ADR-008: Docker Compose for Development, Kubernetes for Production

**Status**: Accepted

**Context**: 
Need deployment strategy for development and production environments.

**Decision**: 
Use Docker Compose for local development and small deployments, Kubernetes for production at scale.

**Rationale**:
1. **Development**: Docker Compose is simple and fast for local setup
2. **Production**: Kubernetes provides scaling, self-healing, rolling updates
3. **Portability**: Both use containers, easy migration path
4. **Team Skills**: Different complexity levels for different environments
5. **Cost**: Docker Compose for POC/testing, K8s when scaling needed

**Consequences**:
- **Positive**: Fast local development, production-ready scalability
- **Negative**: Need to maintain both deployment configurations
- **Neutral**: Can start with Docker Compose and migrate later

**Alternatives Considered**:
1. Kubernetes everywhere (rejected: overkill for development)
2. Docker Compose only (rejected: limited production scaling)
3. Cloud-specific services (rejected: vendor lock-in)

---

## ADR-009: Python for All Services

**Status**: Accepted

**Context**: 
Need to choose languages for sync service and API service.

**Decision**: 
Use Python 3.11+ for both sync service and search API.

**Rationale**:
1. **ML Ecosystem**: Best support for sentence-transformers and ML libraries
2. **Consistency**: Single language for all components
3. **Team Expertise**: Team familiar with Python
4. **Libraries**: Excellent clients for Elasticsearch, Qdrant, MongoDB
5. **Productivity**: Rapid development with strong typing (3.11+)

**Consequences**:
- **Positive**: Code reuse, single skillset, great ML libraries
- **Negative**: Python slower than compiled languages (acceptable for this use case)
- **Neutral**: Need to manage Python version consistency

**Alternatives Considered**:
1. Go for API (rejected: less ML ecosystem, team expertise)
2. Node.js for API (rejected: different language, weaker ML support)
3. Rust (rejected: slower development, steep learning curve)

---

## ADR-010: Incremental Sync with Timestamp Tracking

**Status**: Accepted

**Context**: 
Batch sync can be time-consuming for large datasets. Need efficient sync strategy.

**Decision**: 
Implement incremental sync based on `updated_at` timestamp field, with full sync as fallback.

**Rationale**:
1. **Efficiency**: Only process changed documents
2. **Speed**: Faster sync for routine updates
3. **Resource Usage**: Lower CPU and memory for incremental sync
4. **Flexibility**: Can still do full sync when needed
5. **State Tracking**: Simple timestamp-based tracking

**Consequences**:
- **Positive**: Fast routine syncs, efficient resource usage
- **Negative**: Requires `updated_at` field in source data
- **Neutral**: Need to handle timestamp tracking and recovery

**Alternatives Considered**:
1. Full sync always (rejected: inefficient for large datasets)
2. CDC with change streams (rejected: complexity, see ADR-002)
3. Hash-based change detection (rejected: more complex, slower)

---

## ADR-011: Section-Level Chunking Strategy

**Status**: Accepted

**Context**: 
California legal codes have hierarchical structure with 1,000-20,000 sections each. Need to determine optimal granularity for indexing and search.

**Decision**: 
Index each section as a separate document/vector (one section = one search result) with simple flat metadata for V1.

**Rationale**:
1. **Natural Semantic Boundary**: Sections are complete, self-contained legal concepts
2. **Optimal Size**: Sections typically 100-500 words (fits embedding models well)
3. **Precise Citations**: Results point to exact sections, not vague "page 47"
4. **Right Granularity**: Not too small (losing context) or too large (diluting relevance)
5. **Scalable**: 20,000 sections is tiny for modern search systems
6. **V1 Simplicity**: Flat structure ships faster, can add hierarchy later

**Consequences**:
- **Positive**: Precise results, good performance, natural user experience
- **Negative**: Can't return "entire code" in one result (not needed)
- **Neutral**: 20,000 docs instead of ~30 code docs (still very manageable)

**V1 vs V2**:
- V1 (Now): Use flat fields only (statute_code, title, content, code_name) from existing MongoDB documents
- V2 (Later): Leverage existing hierarchical fields (division, part, chapter) already in MongoDB for navigation and cross-references
- **Key insight**: MongoDB already contains code architecture - we just extract what we need per version

**Alternatives Considered**:
1. Code-level (rejected: too coarse, loses precision)
2. Paragraph-level (rejected: breaks semantic units)
3. Chapter-level (rejected: still too large, arbitrary boundaries)
4. Immediate hierarchical structure (rejected: over-engineering for V1; data exists but features can wait)

---

## Summary of Trade-offs

| Decision | Benefit | Cost | Risk Mitigation |
|----------|---------|------|-----------------|
| Hybrid Architecture | Best search quality | More complexity | Good documentation, monitoring |
| Batch Sync | Simplicity | Eventual consistency | Acceptable for legal codes |
| Self-hosted Embeddings | Cost, privacy | Management overhead | Use standard models, GPU optional |
| RRF Fusion | No tuning needed | Less control | Offer weighted as alternative |
| FastAPI | Modern, fast | Async learning curve | Good documentation, examples |
| MongoDB Source | Existing system | Data duplication | Clear sync process |
| Stateless API | Easy scaling | Caching complexity | Optional Redis cache |
| Docker + K8s | Flexibility | Two configs | Start simple, scale up |

---

## Future Considerations

1. **Fine-tuned Legal Embeddings**: Train domain-specific model on legal corpus
2. **Multi-language Support**: Support Spanish translations of CA codes
3. **Real-time Notifications**: Alert users to new relevant codes
4. **Query Understanding**: NLP to improve query interpretation
5. **Feedback Loop**: Learn from user interactions to improve ranking
6. **Cross-reference Detection**: Automatically link related statutes

