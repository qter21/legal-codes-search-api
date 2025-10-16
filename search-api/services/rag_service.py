"""RAG (Retrieval-Augmented Generation) service for complex queries."""
from typing import List, Dict, Any, Optional
from loguru import logger


class RAGService:
    """
    RAG service that retrieves relevant documents and generates answers using LLM.
    """
    
    def __init__(self, es_service, qdrant_service, embedding_model, llm_service=None):
        """
        Initialize RAG service.
        
        Args:
            es_service: Elasticsearch service for keyword retrieval
            qdrant_service: Qdrant service for semantic retrieval
            embedding_model: Embedding model for query vectorization
            llm_service: Optional LLM service for answer generation
        """
        self.es_service = es_service
        self.qdrant_service = qdrant_service
        self.embedding_model = embedding_model
        self.llm_service = llm_service
        
        if llm_service:
            logger.info("✅ RAG service initialized with LLM generation")
        else:
            logger.info("⚠️ RAG service initialized with template-based generation (no LLM)")
        
        self.use_llm = llm_service is not None
    
    def answer_query(
        self,
        query: str,
        top_k: int = 5,
        context_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Answer complex query using RAG approach.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            context_limit: Number of documents to use as context
        
        Returns:
            Dict with answer and supporting documents
        """
        logger.info(f"RAG query: {query}")
        
        # Step 1: Retrieve relevant documents using hybrid search
        # Use semantic search for complex queries
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Search Qdrant for semantically similar documents
            semantic_results, _ = self.qdrant_service.search(
                query_vector=query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding,
                limit=top_k
            )
            
            # Also get keyword results for context
            keyword_results, _ = self.es_service.search(
                query=query,
                limit=top_k
            )
            
            # Combine and deduplicate
            all_docs = self._merge_results(semantic_results, keyword_results, top_k)
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            # Fallback to keyword search only
            keyword_results, _ = self.es_service.search(query=query, limit=top_k)
            all_docs = keyword_results
        
        # Step 2: Prepare context from top documents
        context_docs = all_docs[:context_limit]
        context = self._build_context(context_docs)
        
        # Step 3: Generate response
        # For now, return structured answer with context
        # In the future, integrate LLM here for actual generation
        response = {
            "query": query,
            "answer_type": "rag",
            "context_used": len(context_docs),
            "relevant_sections": [
                {
                    "code": doc.get('code', doc.get('statute_code', '')),
                    "section": doc.get('section', ''),
                    "content": doc.get('content', '')[:500],
                    "relevance_score": doc.get('score', 0)
                }
                for doc in context_docs
            ],
            "summary": self._generate_summary(query, context_docs),
            "all_results": all_docs[:top_k]
        }
        
        logger.info(f"RAG response generated with {len(context_docs)} context documents")
        return response
    
    def _merge_results(
        self,
        semantic_results: List[Dict],
        keyword_results: List[Dict],
        limit: int
    ) -> List[Dict]:
        """Merge and deduplicate results from semantic and keyword search."""
        seen_ids = set()
        merged = []
        
        # Interleave results (semantic first for complex queries)
        for sem, kw in zip(semantic_results, keyword_results):
            if sem.get('document_id') not in seen_ids:
                merged.append(sem)
                seen_ids.add(sem.get('document_id'))
            if kw.get('document_id') not in seen_ids:
                merged.append(kw)
                seen_ids.add(kw.get('document_id'))
        
        # Add remaining
        for doc in semantic_results + keyword_results:
            if doc.get('document_id') not in seen_ids and len(merged) < limit:
                merged.append(doc)
                seen_ids.add(doc.get('document_id'))
        
        return merged[:limit]
    
    def _build_context(self, documents: List[Dict]) -> str:
        """Build context string from documents."""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            code = doc.get('code', doc.get('statute_code', 'Unknown'))
            section = doc.get('section', 'N/A')
            content = doc.get('content', '')[:500]
            
            context_parts.append(
                f"[{i}] {code} Section {section}:\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _generate_summary(self, query: str, documents: List[Dict]) -> str:
        """
        Generate a summary answer based on retrieved documents.
        
        Uses LLM if available, otherwise falls back to template-based generation.
        """
        if not documents:
            return "No relevant sections found for your query."
        
        # Use LLM if available
        if self.use_llm:
            try:
                return self.llm_service.generate_summary(
                    query=query,
                    documents=documents,
                    max_tokens=300,
                    temperature=0.3
                )
            except Exception as e:
                logger.warning(f"LLM generation failed, falling back to template: {e}")
                # Fall through to template-based generation
        
        # Template-based fallback
        # Count codes mentioned
        codes = {}
        for doc in documents:
            code = doc.get('code', doc.get('statute_code', ''))
            codes[code] = codes.get(code, 0) + 1
        
        # Build summary
        summary_parts = []
        
        # Intro
        if len(codes) == 1:
            code_name = list(codes.keys())[0]
            summary_parts.append(
                f"Your query relates to the {code_name} (California {self._expand_code_name(code_name)})."
            )
        else:
            summary_parts.append(
                f"Your query involves multiple codes: {', '.join(codes.keys())}."
            )
        
        # Main sections
        summary_parts.append(
            f"\nThe most relevant sections are:"
        )
        
        for i, doc in enumerate(documents[:3], 1):
            code = doc.get('code', doc.get('statute_code', ''))
            section = doc.get('section', '')
            summary_parts.append(f"{i}. {code} Section {section}")
        
        # Call to action
        summary_parts.append(
            "\nReview the detailed content below for complete information."
        )
        
        return " ".join(summary_parts)
    
    def _expand_code_name(self, code: str) -> str:
        """Expand code abbreviation to full name."""
        code_names = {
            'FAM': 'Family Code',
            'PEN': 'Penal Code',
            'CIV': 'Civil Code',
            'BPC': 'Business and Professions Code',
            'LAB': 'Labor Code',
            'VEH': 'Vehicle Code',
            'CCP': 'Code of Civil Procedure'
        }
        return code_names.get(code, f"{code} Code")

