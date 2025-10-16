# Quick Start Guide

Get the Legal Codes Search API prototype up and running in 5 minutes.

## Important: Independent Prototype

This is a **standalone testing prototype** that:
- ✅ Runs on port **8888** (separate from your main website)
- ✅ **Only reads** from your existing MongoDB (no data modifications)
- ✅ Completely independent - does not touch codecond_ca website
- ✅ Can be started/stopped anytime without affecting other services

## Prerequisites

- Docker and Docker Compose installed
- 4GB+ available RAM
- Existing MongoDB with CA legal codes data (read-only access)

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd Architecture_design

# Copy environment template
cp env.template .env
```

## Step 2: Configure MongoDB Connection

Edit `.env` file:

```bash
# Update with your MongoDB connection
MONGODB_URL=mongodb://your-mongodb-host:27017
MONGODB_DATABASE=legal_codes
MONGODB_COLLECTION=ca_codes
```

**Important**: Ensure your MongoDB collection contains **section-level documents**:
```json
{
  "statute_code": "CAL-CIVIL-1234",
  "title": "Section 1234 - Property Rights",
  "content": "Full text of section...",
  "code_name": "Civil Code",
  // Hierarchical fields (already in your MongoDB)
  "division": "Division 1",
  "part": "Part 4",
  "chapter": "Chapter 1"
  // V1 sync uses flat fields only
  // V2 will leverage hierarchical fields
}
```

Each document should be one section (not an entire code). For CA codes with 20,000 sections, this creates 20,000 search documents.

**Good news**: Your MongoDB already contains the code architecture (hierarchical structure). V1 uses just the core fields, V2 can add navigation using existing hierarchy data.

For testing with local MongoDB:

```bash
# Uncomment MongoDB service in docker-compose.yml
# Then use:
MONGODB_URL=mongodb://mongodb:27017
```

## Step 3: Start Services

```bash
# Build and start all services
make build
make up

# Or using docker-compose directly
docker-compose build
docker-compose up -d
```

Wait ~30 seconds for services to initialize.

## Step 4: Verify Services

```bash
# Check service health
make health

# Or manually
curl http://localhost:8000/health
```

Expected output (at http://localhost:8888/health):
```json
{
  "status": "healthy",
  "elasticsearch": {
    "connected": true,
    "index": "legal_codes",
    "document_count": 0
  },
  "qdrant": {
    "connected": true,
    "collection": "legal_codes_vectors",
    "point_count": 0
  },
  "embedding_model": {
    "loaded": true,
    "model": "all-MiniLM-L6-v2",
    "dimension": 384
  }
}
```

**Prototype URL**: http://localhost:8888

## Step 5: Run Initial Data Sync

```bash
# Sync data from MongoDB to search engines
make sync

# Or using docker-compose directly
docker-compose run --rm sync-service python sync_job.py
```

This will:
1. Connect to MongoDB
2. Read documents in batches
3. Generate embeddings
4. Index to Elasticsearch and Qdrant

Monitor progress in the logs:
```bash
make logs-sync
```

## Step 6: Test Search

### View API Documentation (Prototype Testing Interface)

Open in browser:
- **Swagger UI**: http://localhost:8888/docs
- **ReDoc**: http://localhost:8888/redoc
- **Health Check**: http://localhost:8888/health

**Remember**: Port 8888 - Your main website is unaffected!

### Test via Command Line

**Keyword Search:**
```bash
make test-keyword

# Or manually
curl -X POST http://localhost:8000/search/keyword \
  -H "Content-Type: application/json" \
  -d '{
    "query": "property rights",
    "limit": 5
  }'
```

**Semantic Search:**
```bash
make test-semantic

# Or manually
curl -X POST http://localhost:8000/search/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what are the rights of property owners?",
    "limit": 5
  }'
```

**Hybrid Search (Recommended):**
```bash
make test-hybrid

# Or manually
curl -X POST http://localhost:8000/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{
    "query": "property rights",
    "limit": 10,
    "fusion_method": "rrf"
  }'
```

## Step 7: Integrate with Your Application

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for detailed integration instructions.

Quick example in Python:

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# Search
response = client.post("/search/hybrid", json={
    "query": "tenant rights California",
    "limit": 10
})

results = response.json()
for result in results["results"]:
    print(f"{result['statute_code']}: {result['title']}")
```

## Common Commands

```bash
# View logs
make logs              # All services
make logs-api          # API only
make logs-sync         # Sync service only

# Restart services
docker-compose restart search-api

# Stop services
make down

# Clean everything (removes data!)
make clean

# Run full re-sync
make sync-full
```

## Troubleshooting

### Services won't start

```bash
# Check if ports are in use
lsof -i :8000  # API port
lsof -i :9200  # Elasticsearch
lsof -i :6333  # Qdrant

# View detailed logs
docker-compose logs
```

### Sync job fails

```bash
# Check MongoDB connection
docker-compose run --rm sync-service python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://your-host:27017')
print(client.server_info())
"

# Check sync logs
docker-compose logs sync-service
```

### Search returns no results

```bash
# Verify data was synced
curl http://localhost:8000/health

# Check document counts
curl http://localhost:9200/legal_codes/_count
curl http://localhost:6333/collections/legal_codes_vectors
```

### Out of memory

```bash
# Reduce memory usage in docker-compose.yml
# For Elasticsearch:
ES_JAVA_OPTS: "-Xms512m -Xmx512m"

# Or stop other services
docker-compose stop <service-name>
```

## Next Steps

1. **Configure**: Customize settings in `config/` directory
2. **Schedule Sync**: Set up automatic syncing (daily recommended)
3. **Production Deploy**: See [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Integrate**: Connect your application using [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
5. **Monitor**: Set up monitoring and alerts

## Getting Help

- Check logs: `make logs`
- Health status: `make health`
- API documentation: http://localhost:8000/docs
- Architecture: [legal-codes-search-architecture.md](legal-codes-search-architecture.md)

## Development

For local development without Docker:

```bash
# Install dependencies
make install

# Run API locally
cd search-api
python main.py

# Run sync locally
cd sync-service
python sync_job.py
```

## Architecture Overview

```
MongoDB (Source) → Sync Service → Elasticsearch + Qdrant
                                         ↓
                                   Search API
                                         ↓
                                  Your Application
```

For detailed architecture, see [legal-codes-search-architecture.md](legal-codes-search-architecture.md).

