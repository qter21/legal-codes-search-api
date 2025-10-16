"""Embedding model wrapper for generating text embeddings."""
from typing import List, Union
import torch
from sentence_transformers import SentenceTransformer
from loguru import logger


class EmbeddingModel:
    """Wrapper for sentence-transformers embedding models."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        max_length: int = 512
    ):
        """
        Initialize the embedding model.
        
        Args:
            model_name: Name of the sentence-transformers model
            device: Device to run on ('cpu', 'cuda', 'mps')
            max_length: Maximum sequence length
        """
        self.model_name = model_name
        self.device = self._get_device(device)
        self.max_length = max_length
        
        logger.info(f"Loading embedding model: {model_name} on {self.device}")
        self.model = SentenceTransformer(model_name, device=self.device)
        self.model.max_seq_length = max_length
        
        # Get embedding dimension
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.dimension}")
    
    def _get_device(self, device: str) -> str:
        """Determine the best available device."""
        if device == "cuda" and torch.cuda.is_available():
            return "cuda"
        elif device == "mps" and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode texts into embeddings.
        
        Args:
            texts: Single text or list of texts to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            normalize: Whether to normalize embeddings
            
        Returns:
            Tensor of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_tensor=True,
            normalize_embeddings=normalize
        )
        
        return embeddings
    
    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Encode a batch of texts and return as list of floats.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors as lists
        """
        embeddings = self.encode(texts, batch_size=batch_size, normalize=True)
        
        # Convert to list of lists
        if isinstance(embeddings, torch.Tensor):
            embeddings = embeddings.cpu().numpy()
        
        return embeddings.tolist()
    
    def combine_fields(
        self,
        document: dict,
        fields: List[str],
        strategy: str = "concat",
        separator: str = " | "
    ) -> str:
        """
        Combine multiple document fields into a single text.
        
        Args:
            document: Document dictionary
            fields: List of field names to combine
            strategy: Combination strategy ('concat' or 'weighted')
            separator: Separator between fields (for concat strategy)
            
        Returns:
            Combined text
        """
        texts = []
        
        for field in fields:
            value = document.get(field, "")
            if value and isinstance(value, str):
                texts.append(value.strip())
        
        if strategy == "concat":
            return separator.join(texts)
        else:
            # For weighted strategy, could add field names as prefixes
            # Example: "Title: ... Section: ... Content: ..."
            weighted_texts = [f"{field.title()}: {text}" 
                            for field, text in zip(fields, texts) if text]
            return " ".join(weighted_texts)
    
    def __repr__(self) -> str:
        return f"EmbeddingModel(model={self.model_name}, device={self.device}, dim={self.dimension})"

