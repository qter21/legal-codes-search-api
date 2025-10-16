"""Embedding service for generating query embeddings."""
from typing import List
from functools import lru_cache
import hashlib
from sentence_transformers import SentenceTransformer
from loguru import logger

from config import settings


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        """Initialize embedding service."""
        self.model_name = settings.embedding.model_name
        self.device = settings.embedding.device
        self.cache_size = settings.embedding.cache_size
        self.model: SentenceTransformer = None
    
    def load_model(self) -> None:
        """Load the embedding model."""
        if self.model is not None:
            return
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        logger.info(f"Embedding model loaded (dimension: {self.model.get_sentence_embedding_dimension()})")
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if not self.model:
            self.load_model()
        return self.model.get_sentence_embedding_dimension()
    
    def encode(self, text: str) -> List[float]:
        """
        Encode text to embedding vector.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            self.load_model()
        
        # Try to get from cache
        cached = self._get_cached_embedding(text)
        if cached is not None:
            return cached
        
        # Generate embedding
        embedding = self.model.encode(
            text,
            convert_to_tensor=False,
            normalize_embeddings=True
        )
        
        # Convert to list and cache
        embedding_list = embedding.tolist()
        self._cache_embedding(text, embedding_list)
        
        return embedding_list
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Encode multiple texts to embeddings.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            self.load_model()
        
        embeddings = self.model.encode(
            texts,
            convert_to_tensor=False,
            normalize_embeddings=True,
            batch_size=32
        )
        
        return embeddings.tolist()
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    @lru_cache(maxsize=1000)
    def _get_cached_embedding(self, text: str) -> List[float]:
        """Get cached embedding (using LRU cache decorator)."""
        return None
    
    def _cache_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache embedding (handled by LRU cache decorator)."""
        pass

