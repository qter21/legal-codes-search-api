# Deployment Guide

This guide covers deploying the Legal Codes Search Architecture to production environments.

## Deployment Options

### Option 1: Docker Compose (Simple Production)

Suitable for small to medium deployments.

#### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 50GB+ storage

#### Steps

1. **Clone and Configure**

```bash
git clone <repository-url>
cd Architecture_design

# Copy and configure environment
cp env.template .env
vim .env  # Update with production values
```

2. **Update Production Configuration**

Edit `docker-compose.yml` for production:

```yaml
# Remove development mounts
# Update resource limits
# Enable restart policies
services:
  search-api:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

3. **Start Services**

```bash
docker-compose up -d
```

4. **Run Initial Sync**

```bash
docker-compose run --rm sync-service python sync_job.py
```

5. **Verify Deployment**

```bash
curl http://localhost:8000/health
```

### Option 2: Kubernetes (Scalable Production)

Suitable for large-scale deployments requiring high availability.

#### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3.0+
- Persistent storage provisioner

#### Deployment Steps

1. **Create Namespace**

```bash
kubectl create namespace legal-search
```

2. **Deploy Elasticsearch**

```bash
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch \
  --namespace legal-search \
  --set replicas=3 \
  --set volumeClaimTemplate.resources.requests.storage=100Gi
```

3. **Deploy Qdrant**

```bash
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm install qdrant qdrant/qdrant \
  --namespace legal-search \
  --set persistence.size=50Gi
```

4. **Deploy Search API**

Create `k8s/search-api-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: search-api
  namespace: legal-search
spec:
  replicas: 3
  selector:
    matchLabels:
      app: search-api
  template:
    metadata:
      labels:
        app: search-api
    spec:
      containers:
      - name: search-api
        image: your-registry/search-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ELASTICSEARCH_URL
          value: "http://elasticsearch-master:9200"
        - name: QDRANT_URL
          value: "http://qdrant:6333"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: search-api
  namespace: legal-search
spec:
  selector:
    app: search-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Apply:

```bash
kubectl apply -f k8s/search-api-deployment.yaml
```

5. **Deploy Sync CronJob**

Create `k8s/sync-cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: legal-codes-sync
  namespace: legal-search
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: sync-service
            image: your-registry/sync-service:latest
            env:
            - name: MONGODB_URL
              valueFrom:
                secretKeyRef:
                  name: mongodb-credentials
                  key: connection_string
            - name: ELASTICSEARCH_URL
              value: "http://elasticsearch-master:9200"
            - name: QDRANT_URL
              value: "http://qdrant:6333"
          restartPolicy: OnFailure
```

Apply:

```bash
kubectl apply -f k8s/sync-cronjob.yaml
```

## Production Configuration

### Elasticsearch Configuration

1. **Heap Size**

```yaml
environment:
  ES_JAVA_OPTS: "-Xms2g -Xmx2g"  # Adjust based on available RAM
```

2. **Cluster Settings**

```bash
# Increase shard allocation awareness
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "85%",
    "cluster.routing.allocation.disk.watermark.high": "90%"
  }
}
'
```

3. **Index Settings**

Update `config/elasticsearch-mapping.json`:

```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 2,
    "refresh_interval": "30s"
  }
}
```

### Qdrant Configuration

1. **Resource Limits**

```yaml
qdrant:
  resources:
    limits:
      memory: 8Gi
      cpu: 4
```

2. **Optimization**

Update `config/qdrant-config.yaml`:

```yaml
hnsw_config:
  m: 16
  ef_construct: 200
  
optimizer_config:
  memmap_threshold: 100000
  indexing_threshold: 50000
```

### API Configuration

1. **Production Settings**

Update `config/api-config.yaml`:

```yaml
api:
  workers: 4  # Adjust based on CPU cores
  
logging:
  level: "WARNING"  # Reduce verbosity in production
  
caching:
  enabled: true
  redis_url: "redis://redis:6379"
  ttl: 3600
```

2. **Rate Limiting**

```yaml
rate_limiting:
  enabled: true
  requests_per_minute: 60
```

## Security

### 1. Elasticsearch Security

Enable X-Pack security:

```yaml
elasticsearch:
  environment:
    xpack.security.enabled: true
    xpack.security.transport.ssl.enabled: true
```

Create users:

```bash
# Create API user
docker-compose exec elasticsearch bin/elasticsearch-users useradd api_user -p <password> -r superuser

# Update connection string
ELASTICSEARCH_URL=http://api_user:<password>@elasticsearch:9200
```

### 2. Qdrant Authentication

Enable API key authentication:

```yaml
qdrant:
  environment:
    QDRANT__SERVICE__API_KEY: "<your-secure-api-key>"
```

### 3. API Authentication

Implement JWT authentication in `search-api/main.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    # Verify JWT token
    if not verify_jwt(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

# Apply to endpoints
@router.post("/search/hybrid", dependencies=[Depends(verify_token)])
async def hybrid_search(...):
    ...
```

### 4. Network Security

Use TLS/SSL:

```bash
# Generate certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt

# Configure in docker-compose or k8s
```

## Monitoring

### 1. Prometheus Metrics

Add to `docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

Create `monitoring/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'elasticsearch'
    static_configs:
      - targets: ['elasticsearch:9200']
  
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
```

### 2. Logging

Centralized logging with ELK:

```yaml
services:
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./monitoring/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
```

### 3. Alerts

Configure alerts in `monitoring/alerts.yml`:

```yaml
groups:
  - name: search_api
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status="500"}[5m]) > 0.05
        annotations:
          summary: "High error rate detected"
      
      - alert: SlowQueries
        expr: histogram_quantile(0.95, rate(query_duration_seconds_bucket[5m])) > 1
        annotations:
          summary: "95th percentile query time > 1s"
```

## Backup and Recovery

### 1. Elasticsearch Snapshots

```bash
# Configure snapshot repository
curl -X PUT "localhost:9200/_snapshot/backup_repo" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backups/elasticsearch"
  }
}
'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_1"
```

### 2. Qdrant Backups

```bash
# Create backup
curl -X POST "http://localhost:6333/collections/legal_codes_vectors/snapshots"

# Download snapshot
curl "http://localhost:6333/collections/legal_codes_vectors/snapshots/<snapshot-name>" \
  --output backup.snapshot
```

### 3. Automated Backups

Create backup cron job in Kubernetes:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-job
spec:
  schedule: "0 3 * * *"  # Daily at 3 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: your-backup-image
            command: ["/bin/sh", "-c"]
            args:
              - |
                # Backup Elasticsearch
                curl -X PUT "elasticsearch:9200/_snapshot/backup_repo/snapshot_$(date +%Y%m%d)"
                
                # Backup Qdrant
                curl -X POST "qdrant:6333/collections/legal_codes_vectors/snapshots"
          restartPolicy: OnFailure
```

## Scaling

### Horizontal Scaling

1. **API Service**

```bash
# Docker Compose
docker-compose up -d --scale search-api=3

# Kubernetes
kubectl scale deployment search-api --replicas=5 -n legal-search
```

2. **Elasticsearch Cluster**

```bash
helm upgrade elasticsearch elastic/elasticsearch \
  --set replicas=5 \
  --namespace legal-search
```

3. **Qdrant Cluster**

Deploy Qdrant in cluster mode with multiple nodes.

### Vertical Scaling

Increase resources:

```yaml
services:
  search-api:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

## Performance Tuning

### 1. Connection Pooling

```python
# In config
elasticsearch:
  max_connections: 50
  max_connections_per_node: 10
```

### 2. Caching

Enable Redis caching:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Update API config:

```yaml
caching:
  enabled: true
  redis_url: "redis://redis:6379"
  ttl: 3600
```

### 3. Load Balancing

Use nginx as reverse proxy:

```nginx
upstream search_api {
    least_conn;
    server search-api-1:8000;
    server search-api-2:8000;
    server search-api-3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://search_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### High Memory Usage

1. Check Elasticsearch heap size
2. Reduce embedding model cache size
3. Adjust Qdrant memory limits

### Slow Queries

1. Check index optimization
2. Review HNSW parameters
3. Enable query caching
4. Reduce retrieve_top_n for hybrid search

### Connection Failures

1. Check network connectivity
2. Verify service health: `kubectl get pods -n legal-search`
3. Review logs: `kubectl logs <pod-name> -n legal-search`

## Maintenance

### Regular Tasks

1. **Weekly**: Review logs and error rates
2. **Monthly**: Update dependencies and security patches
3. **Quarterly**: Performance testing and optimization
4. **Annually**: Capacity planning review

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Verify health
make health
```

## Support

For deployment issues, contact [your DevOps team/support].

