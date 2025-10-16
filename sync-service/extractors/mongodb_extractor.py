"""MongoDB data extractor for batch processing."""
from typing import Dict, Iterator, List, Optional, Any
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from loguru import logger


class MongoDBExtractor:
    """Extract documents from MongoDB in batches."""
    
    def __init__(
        self,
        connection_string: str,
        database: str,
        collection: str,
        batch_size: int = 1000
    ):
        """
        Initialize MongoDB extractor.
        
        Args:
            connection_string: MongoDB connection string
            database: Database name
            collection: Collection name
            batch_size: Number of documents per batch
        """
        self.connection_string = connection_string
        self.database_name = database
        self.collection_name = collection
        self.batch_size = batch_size
        
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
        
    def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            logger.info(f"Connecting to MongoDB: {self.database_name}.{self.collection_name}")
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Test connection
            self.client.server_info()
            logger.info("Successfully connected to MongoDB")
            
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Count total documents matching the query.
        
        Args:
            query: MongoDB query filter
            
        Returns:
            Total document count
        """
        if self.collection is None:
            self.connect()
        
        query = query or {}
        count = self.collection.count_documents(query)
        logger.info(f"Total documents: {count}")
        return count
    
    def extract_batches(
        self,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        sort_by: Optional[List[tuple]] = None
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Extract documents in batches.
        
        Args:
            query: MongoDB query filter
            projection: Fields to include/exclude
            sort_by: List of (field, direction) tuples for sorting
            
        Yields:
            Batches of documents
        """
        if self.collection is None:
            self.connect()
        
        query = query or {}
        sort_by = sort_by or [("_id", 1)]
        
        cursor = self.collection.find(query, projection).sort(sort_by)
        
        batch = []
        total_processed = 0
        
        try:
            for document in cursor:
                # Convert ObjectId to string
                if "_id" in document:
                    document["document_id"] = str(document["_id"])
                
                # Extract content from versions array if top-level content is null/empty
                if not document.get("content") and document.get("versions"):
                    versions = document["versions"]
                    if versions and len(versions) > 0:
                        # Use the first (current) version's content
                        if "content" in versions[0] and versions[0]["content"]:
                            document["content"] = versions[0]["content"]
                        # Also extract legislative history if available
                        if "legislative_history" in versions[0] and versions[0]["legislative_history"]:
                            document["legislative_history"] = versions[0]["legislative_history"]
                
                batch.append(document)
                
                if len(batch) >= self.batch_size:
                    total_processed += len(batch)
                    logger.debug(f"Extracted batch of {len(batch)} documents (total: {total_processed})")
                    yield batch
                    batch = []
            
            # Yield remaining documents
            if batch:
                total_processed += len(batch)
                logger.debug(f"Extracted final batch of {len(batch)} documents (total: {total_processed})")
                yield batch
                
        except PyMongoError as e:
            logger.error(f"Error extracting documents: {e}")
            raise
    
    def extract_incremental(
        self,
        timestamp_field: str,
        last_sync_time: datetime,
        query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Extract documents updated since last sync.
        
        Args:
            timestamp_field: Field name containing update timestamp
            last_sync_time: Timestamp of last sync
            query: Additional query filters
            projection: Fields to include/exclude
            
        Yields:
            Batches of updated documents
        """
        query = query or {}
        query[timestamp_field] = {"$gt": last_sync_time}
        
        logger.info(f"Incremental sync from {last_sync_time}")
        
        return self.extract_batches(
            query=query,
            projection=projection,
            sort_by=[(timestamp_field, 1)]
        )
    
    def get_latest_timestamp(self, timestamp_field: str) -> Optional[datetime]:
        """
        Get the latest timestamp value in the collection.
        
        Args:
            timestamp_field: Field name containing timestamp
            
        Returns:
            Latest timestamp or None
        """
        if self.collection is None:
            self.connect()
        
        result = self.collection.find_one(
            sort=[(timestamp_field, -1)],
            projection={timestamp_field: 1}
        )
        
        if result and timestamp_field in result:
            return result[timestamp_field]
        
        return None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

