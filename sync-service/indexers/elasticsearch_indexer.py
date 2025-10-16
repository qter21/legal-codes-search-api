"""Elasticsearch indexer for legal codes."""
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError
from loguru import logger
import json


class ElasticsearchIndexer:
    """Index documents to Elasticsearch."""
    
    def __init__(
        self,
        url: str,
        index_name: str,
        bulk_size: int = 500,
        timeout: int = 30
    ):
        """
        Initialize Elasticsearch indexer.
        
        Args:
            url: Elasticsearch URL
            index_name: Name of the index
            bulk_size: Number of documents per bulk request
            timeout: Request timeout in seconds
        """
        self.url = url
        self.index_name = index_name
        self.bulk_size = bulk_size
        self.timeout = timeout
        
        self.client: Optional[Elasticsearch] = None
    
    def connect(self) -> None:
        """Connect to Elasticsearch."""
        logger.info(f"Connecting to Elasticsearch: {self.url}")
        self.client = Elasticsearch(
            [self.url],
            request_timeout=self.timeout,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Test connection
        if not self.client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
        
        logger.info("Successfully connected to Elasticsearch")
    
    def disconnect(self) -> None:
        """Close Elasticsearch connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Elasticsearch")
    
    def create_index(self, mapping_file: Optional[str] = None) -> bool:
        """
        Create index with mapping.
        
        Args:
            mapping_file: Path to mapping JSON file
            
        Returns:
            True if index was created, False if it already exists
        """
        if not self.client:
            self.connect()
        
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Index {self.index_name} already exists")
            return False
        
        # Load mapping if provided
        mapping = {}
        if mapping_file:
            try:
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load mapping file: {e}")
        
        self.client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"Created index: {self.index_name}")
        return True
    
    def delete_index(self) -> None:
        """Delete the index."""
        if not self.client:
            self.connect()
        
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
            logger.info(f"Deleted index: {self.index_name}")
    
    def index_document(self, document: Dict[str, Any], doc_id: str) -> None:
        """
        Index a single document.
        
        Args:
            document: Document to index
            doc_id: Document ID
        """
        if not self.client:
            self.connect()
        
        self.client.index(
            index=self.index_name,
            id=doc_id,
            document=document
        )
    
    def index_batch(self, documents: List[Dict[str, Any]]) -> tuple[int, int]:
        """
        Index a batch of documents using bulk API.
        
        Args:
            documents: List of documents to index
            
        Returns:
            Tuple of (success_count, error_count)
        """
        if not self.client:
            self.connect()
        
        if not documents:
            return 0, 0
        
        # Prepare bulk actions
        actions = []
        for doc in documents:
            doc_id = doc.get("document_id") or doc.get("_id")
            if not doc_id:
                logger.warning("Document missing ID, skipping")
                continue
            
            # Remove MongoDB _id if present
            doc_copy = {k: v for k, v in doc.items() if k != "_id"}
            
            action = {
                "_index": self.index_name,
                "_id": str(doc_id),
                "_source": doc_copy
            }
            actions.append(action)
        
        if not actions:
            return 0, 0
        
        try:
            success, failed = bulk(
                self.client,
                actions,
                chunk_size=self.bulk_size,
                raise_on_error=False,
                request_timeout=self.timeout
            )
            
            if failed:
                logger.warning(f"Failed to index {len(failed)} documents")
                for item in failed[:5]:  # Log first 5 errors
                    logger.debug(f"Index error: {item}")
            
            logger.debug(f"Indexed {success} documents, {len(failed)} errors")
            return success, len(failed)
            
        except BulkIndexError as e:
            logger.error(f"Bulk indexing error: {e}")
            return 0, len(documents)
    
    def refresh_index(self) -> None:
        """Refresh the index to make documents searchable."""
        if not self.client:
            self.connect()
        
        self.client.indices.refresh(index=self.index_name)
        logger.debug(f"Refreshed index: {self.index_name}")
    
    def get_document_count(self) -> int:
        """
        Get total document count in index.
        
        Returns:
            Number of documents
        """
        if not self.client:
            self.connect()
        
        count = self.client.count(index=self.index_name)
        return count['count']
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

