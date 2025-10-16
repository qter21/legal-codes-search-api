"""Configuration management for sync service."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class MongoDBConfig(BaseModel):
    """MongoDB configuration."""
    connection_string: str = Field(default="mongodb://localhost:27017")
    database: str = Field(default="legal_codes")
    collection: str = Field(default="ca_codes")
    batch_size: int = Field(default=1000)
    query_filter: Dict[str, Any] = Field(default_factory=dict)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration."""
    url: str = Field(default="http://localhost:9200")
    index_name: str = Field(default="legal_codes")
    bulk_size: int = Field(default=500)
    timeout: int = Field(default=30)


class QdrantConfig(BaseModel):
    """Qdrant configuration."""
    url: str = Field(default="http://localhost:6333")
    collection_name: str = Field(default="legal_codes_vectors")
    batch_size: int = Field(default=100)
    timeout: int = Field(default=30)


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model_name: str = Field(default="ai/embeddinggemma")
    dimension: int = Field(default=768)
    device: str = Field(default="cpu")
    max_length: int = Field(default=512)
    text_fields: List[str] = Field(default=["title", "section", "content"])
    combination_strategy: str = Field(default="concat")
    separator: str = Field(default=" | ")


class SyncConfig(BaseModel):
    """Sync job configuration."""
    schedule: str = Field(default="0 2 * * *")
    timezone: str = Field(default="America/Los_Angeles")
    mode: str = Field(default="incremental")
    timestamp_field: str = Field(default="updated_at")
    state_file: str = Field(default="/app/logs/sync_state.json")
    log_file: str = Field(default="/app/logs/sync.log")
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=5)
    continue_on_error: bool = Field(default=True)


class PerformanceConfig(BaseModel):
    """Performance settings."""
    workers: int = Field(default=4)
    embedding_batch_size: int = Field(default=32)
    prefetch_batches: int = Field(default=2)


class Config(BaseModel):
    """Main configuration."""
    mongodb: MongoDBConfig = Field(default_factory=MongoDBConfig)
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if url := os.getenv("MONGODB_URL"):
            config.mongodb.connection_string = url
        if url := os.getenv("ELASTICSEARCH_URL"):
            config.elasticsearch.url = url
        if url := os.getenv("QDRANT_URL"):
            config.qdrant.url = url
        if batch_size := os.getenv("BATCH_SIZE"):
            config.mongodb.batch_size = int(batch_size)
        if schedule := os.getenv("SYNC_SCHEDULE"):
            config.sync.schedule = schedule
            
        return config


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or environment."""
    if config_path and Path(config_path).exists():
        config = Config.from_yaml(config_path)
    else:
        # Try to load from default location
        default_path = Path(__file__).parent.parent / "config" / "sync-config.yaml"
        if default_path.exists():
            config = Config.from_yaml(str(default_path))
        else:
            config = Config()
    
    # Override with environment variables (always merge env vars)
    if url := os.getenv("MONGODB_URL"):
        config.mongodb.connection_string = url
    if db := os.getenv("MONGODB_DATABASE"):
        config.mongodb.database = db
    if coll := os.getenv("MONGODB_COLLECTION"):
        config.mongodb.collection = coll
    if url := os.getenv("ELASTICSEARCH_URL"):
        config.elasticsearch.url = url
    if url := os.getenv("QDRANT_URL"):
        config.qdrant.url = url
    if batch_size := os.getenv("BATCH_SIZE"):
        config.mongodb.batch_size = int(batch_size)
    if schedule := os.getenv("SYNC_SCHEDULE"):
        config.sync.schedule = schedule
    
    return config

