"""LLM service for natural language generation using local OpenAI-compatible API."""
import httpx
from typing import List, Dict, Any, Optional
from loguru import logger


class LLMService:
    """
    Service for interacting with local LLM (OpenAI-compatible API).
    
    Supports models served via:
    - LM Studio
    - Text Generation WebUI
    - LocalAI
    - Any OpenAI-compatible endpoint
    """
    
    def __init__(
        self,
        api_base: str = "http://127.0.0.1:1234/v1",
        model: str = "openai/gpt-oss-120b",
        timeout: float = 60.0
    ):
        """
        Initialize LLM service.
        
        Args:
            api_base: Base URL for the API
            model: Model name/identifier
            timeout: Request timeout in seconds
        """
        self.api_base = api_base.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        logger.info(f"Initialized LLM service: {model} @ {api_base}")
        
        # Verify connection
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """Verify connection to LLM API."""
        try:
            response = self.client.get(f"{self.api_base}/models")
            response.raise_for_status()
            logger.info(f"✅ LLM API connected successfully")
            return True
        except Exception as e:
            logger.warning(f"⚠️ LLM API not accessible: {e}. Will attempt to use on-demand.")
            return False
    
    def generate_answer(
        self,
        query: str,
        context: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate an answer to a query given context.
        
        Args:
            query: User's question
            context: Relevant context from retrieved documents
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0, lower = more focused)
            system_prompt: Optional system prompt override
        
        Returns:
            Generated answer text
        """
        if system_prompt is None:
            system_prompt = """You are an expert legal assistant specializing in California law. 
Your role is to provide accurate, clear, and helpful information about California legal codes.

Guidelines:
1. Base your answers ONLY on the provided legal code sections
2. Be precise and cite specific sections when relevant
3. Use clear, accessible language while maintaining legal accuracy
4. If the context doesn't contain enough information, say so
5. Do not make up or infer information not present in the context
6. Structure your answer logically with sections or bullet points when appropriate"""
        
        # Build user prompt
        user_prompt = f"""Based on the following California legal code sections, please answer this question:

Question: {query}

Relevant Legal Code Sections:
{context}

Please provide a clear, accurate answer based on these sections. Cite specific sections where relevant."""
        
        try:
            response = self.client.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False
                }
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            
            logger.info(f"Generated answer ({len(answer)} chars) for query: {query[:50]}...")
            return answer
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during LLM generation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during LLM generation: {e}")
            raise
    
    def generate_summary(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        max_tokens: int = 300,
        temperature: float = 0.3
    ) -> str:
        """
        Generate a concise summary answer from documents.
        
        Args:
            query: User's question
            documents: List of relevant documents
            max_tokens: Maximum tokens for summary
            temperature: Sampling temperature
        
        Returns:
            Generated summary
        """
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(documents[:5], 1):  # Top 5 docs
            code = doc.get('code', doc.get('statute_code', 'Unknown'))
            section = doc.get('section', 'N/A')
            content = doc.get('content', '')[:500]  # First 500 chars
            
            context_parts.append(
                f"[{i}] {code} Section {section}:\n{content}\n"
            )
        
        context = "\n".join(context_parts)
        
        # Generate answer
        return self.generate_answer(
            query=query,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    def generate_comparison(
        self,
        query: str,
        sections: List[Dict[str, Any]],
        max_tokens: int = 600
    ) -> str:
        """
        Generate a comparison between multiple legal code sections.
        
        Args:
            query: Comparison query
            sections: List of sections to compare
            max_tokens: Maximum tokens to generate
        
        Returns:
            Comparison analysis
        """
        system_prompt = """You are an expert legal analyst specializing in California law.
Your role is to compare and contrast different legal code sections, highlighting:
- Key similarities
- Important differences
- Practical implications
- How they relate to each other

Be precise, cite sections, and structure your comparison clearly."""
        
        # Build context
        context_parts = []
        for i, sec in enumerate(sections, 1):
            code = sec.get('code', sec.get('statute_code', 'Unknown'))
            section = sec.get('section', 'N/A')
            content = sec.get('content', '')
            
            context_parts.append(
                f"Section {i}: {code} Section {section}\n{content}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        return self.generate_answer(
            query=query,
            context=context,
            max_tokens=max_tokens,
            temperature=0.3,
            system_prompt=system_prompt
        )
    
    def explain_section(
        self,
        section_code: str,
        section_number: str,
        content: str,
        max_tokens: int = 400
    ) -> str:
        """
        Generate a plain-language explanation of a legal code section.
        
        Args:
            section_code: Code abbreviation (e.g., FAM, PEN)
            section_number: Section number
            content: Section content
            max_tokens: Maximum tokens to generate
        
        Returns:
            Plain-language explanation
        """
        system_prompt = """You are a legal educator specializing in California law.
Your role is to explain legal code sections in clear, accessible language that non-lawyers can understand.

Guidelines:
1. Start with a brief overview of what the section addresses
2. Break down complex legal language into plain terms
3. Provide practical examples when helpful
4. Highlight key requirements, rights, or obligations
5. Note any important exceptions or conditions
6. Keep explanations concise and focused"""
        
        query = f"Please explain what {section_code} Section {section_number} means in plain language."
        
        context = f"{section_code} Section {section_number}:\n{content}"
        
        return self.generate_answer(
            query=query,
            context=context,
            max_tokens=max_tokens,
            temperature=0.4,  # Slightly higher for more natural explanations
            system_prompt=system_prompt
        )
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
        logger.info("LLM service closed")

