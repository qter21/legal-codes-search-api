"""Main sync job orchestrator for legal codes data pipeline."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
from tqdm import tqdm

from config import load_config
from models.embedding_model import EmbeddingModel
from services.docker_model_embedding import DockerModelEmbeddingService
from extractors.mongodb_extractor import MongoDBExtractor
from indexers.elasticsearch_indexer import ElasticsearchIndexer
from indexers.qdrant_indexer import QdrantIndexer
from indexers.qdrant_http_indexer import QdrantHTTPIndexer


class SyncState:
    """Manage sync state persistence."""
    
    def __init__(self, state_file: str):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """Load sync state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return {}
    
    def save(self, state: Dict[str, Any]) -> None:
        """Save sync state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")


class SyncJob:
    """Orchestrate data synchronization from MongoDB to search engines."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize sync job."""
        self.config = load_config(config_path)
        self.state_manager = SyncState(self.config.sync.state_file)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.embedding_model: Optional[EmbeddingModel] = None
        self.mongodb_extractor: Optional[MongoDBExtractor] = None
        self.es_indexer: Optional[ElasticsearchIndexer] = None
        self.qdrant_indexer: Optional[QdrantIndexer] = None
        
        # Statistics
        self.stats = {
            "total_documents": 0,
            "processed_documents": 0,
            "es_success": 0,
            "es_errors": 0,
            "qdrant_success": 0,
            "qdrant_errors": 0,
            "start_time": None,
            "end_time": None,
        }
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        log_file = Path(self.config.sync.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.remove()  # Remove default handler
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
        )
        logger.add(
            log_file,
            level="DEBUG",
            rotation="10 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
        )
    
    def initialize_components(self) -> None:
        """Initialize all components."""
        logger.info("Initializing components...")
        
        # Initialize embedding model (use Docker Model Runner if available)
        logger.info(f"Loading embedding model: {self.config.embedding.model_name}")
        try:
            # Try Docker Model Runner first (ai/embeddinggemma)
            self.embedding_model = DockerModelEmbeddingService("ai/embeddinggemma")
            logger.info("✅ Using Docker Model Runner (ai/embeddinggemma, 768-dim) for embeddings")
        except Exception as e:
            # Fall back to sentence-transformers
            logger.warning(f"Docker Model not available, using sentence-transformers: {e}")
            self.embedding_model = EmbeddingModel(
                model_name=self.config.embedding.model_name,
                device=self.config.embedding.device,
                max_length=self.config.embedding.max_length
            )
        
        # Initialize extractors and indexers
        self.mongodb_extractor = MongoDBExtractor(
            connection_string=self.config.mongodb.connection_string,
            database=self.config.mongodb.database,
            collection=self.config.mongodb.collection,
            batch_size=self.config.mongodb.batch_size
        )
        
        self.es_indexer = ElasticsearchIndexer(
            url=self.config.elasticsearch.url,
            index_name=self.config.elasticsearch.index_name,
            bulk_size=self.config.elasticsearch.bulk_size,
            timeout=self.config.elasticsearch.timeout
        )
        
        # Use HTTP-based indexer (bypasses qdrant-client formatting issues)
        self.qdrant_indexer = QdrantHTTPIndexer(
            url=self.config.qdrant.url,
            collection_name=self.config.qdrant.collection_name,
            vector_dimension=self.config.embedding.dimension
        )
        
        # Connect to services
        self.mongodb_extractor.connect()
        self.es_indexer.connect()
        self.qdrant_indexer.connect()
        
        # Ensure indexes exist
        mapping_file = Path(__file__).parent.parent / "config" / "elasticsearch-mapping.json"
        if mapping_file.exists():
            self.es_indexer.create_index(str(mapping_file))
        else:
            self.es_indexer.create_index()
        
        self.qdrant_indexer.ensure_collection()
        
        logger.info("All components initialized successfully")
    
    def cleanup_components(self) -> None:
        """Cleanup and disconnect all components."""
        if self.mongodb_extractor:
            self.mongodb_extractor.disconnect()
        if self.es_indexer:
            self.es_indexer.disconnect()
        if self.qdrant_indexer:
            self.qdrant_indexer.disconnect()
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get timestamp of last successful sync."""
        state = self.state_manager.load()
        if "last_sync_time" in state:
            return datetime.fromisoformat(state["last_sync_time"])
        return None
    
    def process_batch(self, documents: list) -> None:
        """
        Process a batch of documents.
        
        Args:
            documents: List of documents to process
        """
        if not documents:
            return
        
        # Prepare texts for embedding
        texts = []
        for doc in documents:
            combined_text = self.embedding_model.combine_fields(
                document=doc,
                fields=self.config.embedding.text_fields,
                strategy=self.config.embedding.combination_strategy,
                separator=self.config.embedding.separator
            )
            texts.append(combined_text)
        
        # Generate embeddings
        logger.debug(f"Generating embeddings for {len(texts)} documents...")
        embeddings = self.embedding_model.encode_batch(
            texts,
            batch_size=self.config.performance.embedding_batch_size
        )
        
        # Index to Elasticsearch
        logger.debug(f"Indexing to Elasticsearch...")
        es_success, es_errors = self.es_indexer.index_batch(documents)
        self.stats["es_success"] += es_success
        self.stats["es_errors"] += es_errors
        
        # Prepare payloads for Qdrant (lightweight metadata only)
        payloads = []
        point_ids = []
        for doc in documents:
            payload = {
                "document_id": doc.get("document_id"),
                "code": doc.get("code", ""),
                "section": doc.get("section", "")[:200],
                "content_preview": doc.get("content", "")[:500],  # First 500 chars
            }
            # Add hierarchical fields if present
            if "division" in doc and doc.get("division"):
                payload["division"] = str(doc["division"])
            if "part" in doc and doc.get("part"):
                payload["part"] = str(doc["part"])
            if "chapter" in doc and doc.get("chapter"):
                payload["chapter"] = str(doc["chapter"])
            
            payloads.append(payload)
            point_ids.append(doc.get("document_id"))
        
        # Index to Qdrant (convert numpy arrays to lists)
        logger.debug(f"Indexing to Qdrant...")
        vectors_as_lists = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings]
        qdrant_success, qdrant_errors = self.qdrant_indexer.index_batch(
            vectors=vectors_as_lists,
            payloads=payloads,
            point_ids=point_ids
        )
        self.stats["qdrant_success"] += qdrant_success
        self.stats["qdrant_errors"] += qdrant_errors
        
        self.stats["processed_documents"] += len(documents)
    
    def run_full_sync(self) -> None:
        """Run full synchronization of all documents."""
        logger.info("Starting FULL sync...")
        
        # Count total documents
        self.stats["total_documents"] = self.mongodb_extractor.count_documents(
            query=self.config.mongodb.query_filter
        )
        
        if self.stats["total_documents"] == 0:
            logger.warning("No documents to sync")
            return
        
        # Extract and process batches
        with tqdm(total=self.stats["total_documents"], desc="Syncing") as pbar:
            for batch in self.mongodb_extractor.extract_batches(
                query=self.config.mongodb.query_filter
            ):
                try:
                    self.process_batch(batch)
                    pbar.update(len(batch))
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    if not self.config.sync.continue_on_error:
                        raise
    
    def run_incremental_sync(self) -> None:
        """Run incremental synchronization of updated documents."""
        logger.info("Starting INCREMENTAL sync...")
        
        last_sync_time = self.get_last_sync_time()
        if not last_sync_time:
            logger.warning("No last sync time found, running full sync")
            return self.run_full_sync()
        
        logger.info(f"Syncing documents updated since {last_sync_time}")
        
        # Count documents to sync
        query = self.config.mongodb.query_filter.copy()
        query[self.config.sync.timestamp_field] = {"$gt": last_sync_time}
        self.stats["total_documents"] = self.mongodb_extractor.count_documents(query)
        
        if self.stats["total_documents"] == 0:
            logger.info("No new documents to sync")
            return
        
        # Extract and process batches
        with tqdm(total=self.stats["total_documents"], desc="Syncing") as pbar:
            for batch in self.mongodb_extractor.extract_incremental(
                timestamp_field=self.config.sync.timestamp_field,
                last_sync_time=last_sync_time,
                query=self.config.mongodb.query_filter
            ):
                try:
                    self.process_batch(batch)
                    pbar.update(len(batch))
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    if not self.config.sync.continue_on_error:
                        raise
    
    def run(self) -> None:
        """Main sync job execution."""
        self.stats["start_time"] = datetime.now(timezone.utc)
        
        try:
            logger.info("=" * 70)
            logger.info("Starting Legal Codes Sync Job")
            logger.info("=" * 70)
            
            # Initialize
            self.initialize_components()
            
            # Run sync based on mode
            if self.config.sync.mode == "full":
                self.run_full_sync()
            elif self.config.sync.mode == "incremental":
                self.run_incremental_sync()
            else:
                logger.error(f"Unknown sync mode: {self.config.sync.mode}")
                return
            
            # Refresh indexes
            logger.info("Refreshing indexes...")
            self.es_indexer.refresh_index()
            
            # Save state
            self.stats["end_time"] = datetime.now(timezone.utc)
            state = {
                "last_sync_time": self.stats["end_time"].isoformat(),
                "last_sync_stats": self.stats,
            }
            self.state_manager.save(state)
            
            # Print summary
            self._print_summary()
            
        except Exception as e:
            logger.exception(f"Sync job failed: {e}")
            raise
        finally:
            self.cleanup_components()
    
    def _print_summary(self) -> None:
        """Print sync job summary."""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        logger.info("=" * 70)
        logger.info("Sync Job Summary")
        logger.info("=" * 70)
        logger.info(f"Total documents:     {self.stats['total_documents']}")
        logger.info(f"Processed:           {self.stats['processed_documents']}")
        logger.info(f"Elasticsearch:       {self.stats['es_success']} success, {self.stats['es_errors']} errors")
        logger.info(f"Qdrant:              {self.stats['qdrant_success']} success, {self.stats['qdrant_errors']} errors")
        logger.info(f"Duration:            {duration:.2f} seconds")
        
        if self.stats['processed_documents'] > 0:
            rate = self.stats['processed_documents'] / duration
            logger.info(f"Throughput:          {rate:.2f} docs/second")
        
        logger.info("=" * 70)


def main():
    """Main entry point."""
    config_path = Path(__file__).parent.parent / "config" / "sync-config.yaml"
    
    sync_job = SyncJob(str(config_path) if config_path.exists() else None)
    sync_job.run()


if __name__ == "__main__":
    main()

