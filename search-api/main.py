"""Main FastAPI application for legal codes search API."""
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
from contextlib import asynccontextmanager

from config import settings
from models.response import HealthResponse
from services.elasticsearch_service import ElasticsearchService
from services.qdrant_service import QdrantService
from services.embedding_service import EmbeddingService
from services.hybrid_search import HybridSearchService
from services.llm_service import LLMService
from routers import search, intelligent_search


# Initialize services (will be set in lifespan)
es_service = None
qdrant_service = None
embedding_service = None
hybrid_search_service = None
llm_service = None  # Optional LLM service


def setup_logging():
    """Configure logging."""
    log_file = Path(settings.logging.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=settings.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global es_service, qdrant_service, embedding_service, hybrid_search_service, llm_service
    
    # Startup
    logger.info("Starting Legal Codes Search API...")
    setup_logging()
    
    try:
        # Initialize services
        logger.info("Initializing services...")
        
        es_service = ElasticsearchService()
        es_service.connect()
        
        qdrant_service = QdrantService()
        qdrant_service.connect()
        
        embedding_service = EmbeddingService()
        embedding_service.load_model()
        
        hybrid_search_service = HybridSearchService(
            es_service=es_service,
            qdrant_service=qdrant_service,
            embedding_service=embedding_service
        )
        
        # LLM service (optional)
        try:
            llm_service = LLMService(
                api_base=os.getenv("LLM_API_BASE", "http://127.0.0.1:1234/v1"),
                model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
                timeout=float(os.getenv("LLM_TIMEOUT", "60.0"))
            )
            logger.info("✅ LLM service initialized (RAG will use natural language generation)")
        except Exception as e:
            logger.warning(f"⚠️ LLM service not available: {e}. RAG will use template-based generation.")
            llm_service = None
        
        # Set services in router module
        search.es_service = es_service
        search.qdrant_service = qdrant_service
        search.embedding_service = embedding_service
        search.hybrid_search_service = hybrid_search_service
        
        logger.info("All services initialized successfully")
        
        yield
        
        # Shutdown
        logger.info("Shutting down services...")
        if es_service:
            es_service.close()
        if qdrant_service:
            qdrant_service.close()
        if llm_service:
            llm_service.close()
        logger.info("Shutdown complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


# Create FastAPI app
app = FastAPI(
    title=settings.api.title,
    version=settings.api.version,
    description=settings.api.description,
    lifespan=lifespan
)


# Configure CORS
if settings.cors.enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )


# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(search.router)
app.include_router(intelligent_search.router)


@app.get("/", tags=["root"], include_in_schema=False)
async def root():
    """Serve the main search interface or API information."""
    static_file = static_dir / "index.html"
    if static_file.exists():
        return FileResponse(static_file)
    
    return {
        "name": settings.api.title,
        "version": settings.api.version,
        "description": settings.api.description,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "search": {
                "keyword": "/search/keyword",
                "semantic": "/search/semantic",
                "hybrid": "/search/hybrid"
            }
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the status of all services including Elasticsearch,
    Qdrant, and the embedding model.
    """
    try:
        # Check Elasticsearch
        es_connected = es_service.is_healthy() if es_service else False
        es_doc_count = es_service.get_document_count() if es_connected else 0
        
        # Check Qdrant
        qdrant_connected = qdrant_service.is_healthy() if qdrant_service else False
        qdrant_point_count = qdrant_service.get_point_count() if qdrant_connected else 0
        
        # Check embedding model
        embedding_loaded = embedding_service.is_loaded() if embedding_service else False
        embedding_dim = embedding_service.get_dimension() if embedding_loaded else 0
        
        # Determine overall status
        all_healthy = es_connected and qdrant_connected and embedding_loaded
        status = "healthy" if all_healthy else "degraded"
        
        return HealthResponse(
            status=status,
            elasticsearch={
                "connected": es_connected,
                "index": settings.elasticsearch.index_name,
                "document_count": es_doc_count
            },
            qdrant={
                "connected": qdrant_connected,
                "collection": settings.qdrant.collection_name,
                "point_count": qdrant_point_count
            },
            embedding_model={
                "loaded": embedding_loaded,
                "model": settings.embedding.model_name,
                "dimension": embedding_dim
            }
        )
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=True
    )

