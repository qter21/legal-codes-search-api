"""Configuration management for search API."""
import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class APIConfig(BaseModel):
    """API server configuration."""
    title: str = Field(default="Legal Codes Search API")
    version: str = Field(default="1.0.0")
    description: str = Field(default="Hybrid search API for California legal codes")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)


class ElasticsearchConfig(BaseModel):
    """Elasticsearch configuration."""
    url: str = Field(default_factory=lambda: os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200'))
    index_name: str = Field(default="legal_codes")
    timeout: int = Field(default=10)
    max_retries: int = Field(default=3)


class QdrantConfig(BaseModel):
    """Qdrant configuration."""
    url: str = Field(default_factory=lambda: os.getenv('QDRANT_URL', 'http://localhost:6333'))
    collection_name: str = Field(default="legal_codes_vectors")
    timeout: int = Field(default=10)
    max_retries: int = Field(default=3)


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    model_name: str = Field(default="all-MiniLM-L6-v2")
    dimension: int = Field(default=384)
    device: str = Field(default="cpu")
    cache_size: int = Field(default=1000)


class KeywordSearchConfig(BaseModel):
    """Keyword search settings."""
    default_fields: List[str] = Field(default=["title^3", "section^2", "content"])
    fuzziness: str = Field(default="AUTO")
    minimum_should_match: str = Field(default="75%")


class SemanticSearchConfig(BaseModel):
    """Semantic search settings."""
    score_threshold: float = Field(default=0.7)
    ef_search: int = Field(default=100)


class HybridSearchConfig(BaseModel):
    """Hybrid search settings."""
    fusion_method: str = Field(default="rrf")
    keyword_weight: float = Field(default=0.5)
    semantic_weight: float = Field(default=0.5)
    rrf_k: int = Field(default=60)
    retrieve_top_n: int = Field(default=50)


class SearchConfig(BaseModel):
    """Search configuration."""
    default_limit: int = Field(default=10)
    max_limit: int = Field(default=100)
    keyword: KeywordSearchConfig = Field(default_factory=KeywordSearchConfig)
    semantic: SemanticSearchConfig = Field(default_factory=SemanticSearchConfig)
    hybrid: HybridSearchConfig = Field(default_factory=HybridSearchConfig)


class PaginationConfig(BaseModel):
    """Pagination configuration."""
    default_page: int = Field(default=1)
    default_page_size: int = Field(default=10)
    max_page_size: int = Field(default=100)


class CORSConfig(BaseModel):
    """CORS configuration."""
    enabled: bool = Field(default=True)
    origins: List[str] = Field(default=["http://localhost:3000"])
    allow_credentials: bool = Field(default=True)
    allow_methods: List[str] = Field(default=["GET", "POST"])
    allow_headers: List[str] = Field(default=["*"])


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    file: str = Field(default="/app/logs/api.log")


class Settings(BaseSettings):
    """Application settings."""
    api: APIConfig = Field(default_factory=APIConfig)
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


def load_settings(config_path: Optional[str] = None) -> Settings:
    """Load settings from YAML file and environment (env vars take precedence)."""
    # Start with defaults from environment
    settings = Settings()
    
    # Override with YAML if exists (but env vars still take precedence via pydantic)
    config_dict = {}
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f) or {}
    else:
        # Try default location
        default_path = Path(__file__).parent.parent / "config" / "api-config.yaml"
        if default_path.exists():
            with open(default_path, 'r') as f:
                config_dict = yaml.safe_load(f) or {}
    
    # Merge: env vars from Settings() override YAML values
    if config_dict:
        # Use env var if set, otherwise use YAML value
        if 'elasticsearch' in config_dict:
            settings.elasticsearch.url = os.getenv('ELASTICSEARCH_URL', config_dict['elasticsearch'].get('url', settings.elasticsearch.url))
        if 'qdrant' in config_dict:
            settings.qdrant.url = os.getenv('QDRANT_URL', config_dict['qdrant'].get('url', settings.qdrant.url))
    
    return settings


# Global settings instance
settings = load_settings()

