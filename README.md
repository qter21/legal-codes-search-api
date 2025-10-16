# Legal Codes Search Architecture

**Version**: v0.1.0 (MVP)  
**Status**: Functional prototype for testing and feedback  
**Release Date**: October 16, 2025

A hybrid search system combining Elasticsearch (keyword search) and Qdrant (semantic vector search) for California legal codes, with MongoDB as the source of truth. This MVP includes AI-powered intelligent search with local LLM integration.

## Architecture Overview

```
┌─────────────────┐
│   codecond_ca   │ (Client Application)
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
     │  Sync Service   │ (Scheduled Batch Job)
     │  + Embedding    │
     └────────┬────────┘
              │
              ▼
     ┌────────────────┐
     │    MongoDB     │ (Source of Truth)
     └────────────────┘
```

## Features

- **Keyword Search**: Traditional full-text search using Elasticsearch with BM25 ranking
- **Semantic Search**: Vector-based similarity search using Qdrant and sentence embeddings
- **Hybrid Search**: Combines both methods using Reciprocal Rank Fusion (RRF)
- **Section-Level Search**: Each legal code section is indexed separately for precise results
- **Batch Sync**: Scheduled synchronization from MongoDB to search engines
- **Self-hosted Embeddings**: Uses sentence-transformers for cost-effective embedding generation

## Data Model (V1)

**Each MongoDB document represents one section** of California legal code:
- One section = one search result
- Optimal for codes with 1,000-20,000 sections
- MongoDB contains both section content AND code architecture (hierarchical structure)
- **V1**: Use flat fields only (statute_code, title, content, code_name)
- **V2**: Leverage existing hierarchical fields (division, part, chapter) - no schema changes needed!

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- MongoDB instance (or use the included one for testing)

### 1. Start Services

```bash
# Start all services (Elasticsearch, Qdrant, API, Sync)
docker-compose up -d

# Check service health (runs on port 8888)
curl http://localhost:8888/health
```

**Note**: This is an **independent prototype** for testing. It runs on port 8888 and only reads from your existing MongoDB (no modifications to your data or main website).

### 2. Run Initial Sync

```bash
# Run sync service to populate search engines
docker-compose run sync-service python sync_job.py
```

### 3. Try the API

```bash
# Keyword search
curl -X POST http://localhost:8000/search/keyword \
  -H "Content-Type: application/json" \
  -d '{"query": "civil code property", "limit": 10}'

# Semantic search
curl -X POST http://localhost:8000/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "property ownership rights", "limit": 10}'

# Hybrid search (recommended)
curl -X POST http://localhost:8000/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{"query": "property rights", "limit": 10, "fusion_method": "rrf"}'
```

### 4. View API Documentation

Open your browser to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
Architecture_design/
├── config/                      # Configuration files
│   ├── api-config.yaml         # Search API configuration
│   ├── sync-config.yaml        # Sync service configuration
│   ├── elasticsearch-mapping.json
│   └── qdrant-config.yaml
├── sync-service/               # Data synchronization service
│   ├── models/
│   │   └── embedding_model.py  # Embedding model wrapper
│   ├── extractors/
│   │   └── mongodb_extractor.py
│   ├── indexers/
│   │   ├── elasticsearch_indexer.py
│   │   └── qdrant_indexer.py
│   ├── sync_job.py            # Main sync orchestrator
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── search-api/                 # Search API service
│   ├── routers/
│   │   └── search.py          # Search endpoints
│   ├── services/
│   │   ├── elasticsearch_service.py
│   │   ├── qdrant_service.py
│   │   ├── embedding_service.py
│   │   └── hybrid_search.py   # Result fusion logic
│   ├── models/
│   │   ├── request.py
│   │   └── response.py
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
└── docker-compose.yml
```

## Configuration

### MongoDB Connection

Update `config/sync-config.yaml`:

```yaml
mongodb:
  connection_string: "mongodb://your-mongodb-host:27017"
  database: "legal_codes"
  collection: "ca_codes"
```

### Embedding Model Selection

Choose between models in `config/sync-config.yaml` and `config/api-config.yaml`:

```yaml
embedding:
  model_name: "all-MiniLM-L6-v2"  # Fast, 384-dim
  # OR
  model_name: "legal-bert-base-uncased"  # Domain-specific, 768-dim
```

### Sync Schedule

Configure batch sync schedule in `config/sync-config.yaml`:

```yaml
sync:
  schedule: "0 2 * * *"  # Daily at 2 AM (cron format)
  mode: "incremental"     # or "full"
  timestamp_field: "updated_at"
```

## API Endpoints

### POST /search/keyword

Traditional keyword search using Elasticsearch.

```json
{
  "query": "civil code section 1234",
  "limit": 10,
  "offset": 0,
  "filters": {
    "statute_code": "CAL-CIVIL-1234"
  }
}
```

### POST /search/semantic

Semantic vector search using Qdrant.

```json
{
  "query": "property ownership and rights",
  "limit": 10,
  "score_threshold": 0.7
}
```

### POST /search/hybrid

Hybrid search combining both methods.

```json
{
  "query": "property rights California",
  "limit": 10,
  "fusion_method": "rrf",
  "keyword_weight": 0.5,
  "semantic_weight": 0.5
}
```

## Development

### Local Development Setup

```bash
# Install dependencies
cd search-api
pip install -r requirements.txt

cd ../sync-service
pip install -r requirements.txt

# Run API locally
cd search-api
python main.py

# Run sync job locally
cd sync-service
python sync_job.py
```

### Running Tests

```bash
# Run search API tests
cd search-api
pytest tests/

# Run sync service tests
cd sync-service
pytest tests/
```

## Performance Tuning

### Elasticsearch

- Adjust `number_of_shards` in mapping based on data size
- Tune analyzers for legal text specificity
- Configure heap size via `ES_JAVA_OPTS`

### Qdrant

- Adjust HNSW parameters (`m`, `ef_construct`) in `qdrant-config.yaml`
- Increase `ef_search` for better accuracy (slower)
- Use SSD storage for optimal performance

### Embedding Generation

- Use GPU if available: `device: "cuda"` in config
- Adjust `embedding_batch_size` for memory/speed tradeoff
- Consider model quantization for production

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Returns status of all services including document/vector counts.

### Logs

- API logs: `search-api/logs/api.log`
- Sync logs: `sync-service/logs/sync.log`
- Sync state: `sync-service/logs/sync_state.json`

### Metrics

Access Elasticsearch metrics:
```bash
curl http://localhost:9200/_cluster/health
curl http://localhost:9200/legal_codes/_stats
```

Access Qdrant metrics:
```bash
curl http://localhost:6333/collections/legal_codes_vectors
```

## Production Deployment

### Recommended Setup

1. **Elasticsearch Cluster**: 3+ nodes for high availability
2. **Qdrant**: Persistent volume for data storage
3. **API Service**: Multiple replicas behind load balancer
4. **Sync Service**: Kubernetes CronJob or similar scheduler
5. **Monitoring**: Prometheus + Grafana for metrics

### Security Considerations

- Enable Elasticsearch security features
- Use authentication for Qdrant
- Implement API authentication/authorization
- Use TLS/SSL for all connections
- Secure MongoDB connection string

## Troubleshooting

### Sync Job Fails

1. Check MongoDB connection: `docker-compose logs sync-service`
2. Verify Elasticsearch/Qdrant are running: `docker-compose ps`
3. Check sync state file: `cat sync-service/logs/sync_state.json`

### Search Returns No Results

1. Verify data was synced: Check health endpoint
2. Check index/collection names match configuration
3. Review query parameters and filters

### High Latency

1. Reduce `retrieve_top_n` in hybrid search config
2. Enable result caching (Redis)
3. Optimize Elasticsearch field mappings
4. Tune Qdrant HNSW parameters

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

## Support

For issues and questions, please contact [your contact info].

