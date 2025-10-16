"""Intelligent query classification for routing between simple and complex search."""
import re
from typing import Tuple, Dict, Any
from loguru import logger


class QueryClassifier:
    """Classify queries as simple (code/section lookup) or complex (semantic/RAG)."""
    
    # Patterns for code/section references
    CODE_PATTERNS = [
        # "FAM 3044", "Family Code 3044", "FC 3044"
        r'\b(FAM|PEN|CIV|BPC|LAB|VEH|CCP|FC|PC|CC|BP|LC|VC)\s*\d+',
        # "Section 3044", "§3044", "3044"
        r'\b(section|sec|§)\s*\d+',
        # Just numbers with context
        r'\b\d{3,5}\b',
        # "California Family Code 3044"
        r'\b(california|ca)?\s*(family|penal|civil|business|labor|vehicle|code)\s*(code)?\s*\d+',
    ]
    
    # Keywords that indicate simple lookup
    SIMPLE_KEYWORDS = {
        'section', 'code', 'statute', 'law', 'what is', 'define', 'definition',
        'text of', 'show me', 'find', 'lookup', 'cite', 'citation'
    }
    
    # Keywords that indicate complex/semantic query
    COMPLEX_KEYWORDS = {
        'how', 'why', 'when', 'explain', 'describe', 'compare', 'difference',
        'what are', 'tell me about', 'help me understand', 'can i', 'should i',
        'example', 'requirements', 'process', 'procedure', 'steps', 'rights',
        'obligations', 'penalties', 'consequences', 'applies to', 'does this mean'
    }
    
    def __init__(self):
        """Initialize query classifier."""
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.CODE_PATTERNS]
        logger.info("Query classifier initialized")
    
    def classify(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Classify query as 'simple' or 'complex'.
        
        Args:
            query: User query string
        
        Returns:
            Tuple of (classification, metadata)
            - classification: 'simple' or 'complex'
            - metadata: Dict with extraction details
        """
        query_lower = query.lower().strip()
        metadata = {
            'query': query,
            'query_length': len(query),
            'has_code_reference': False,
            'extracted_codes': [],
            'extracted_sections': [],
            'simple_score': 0,
            'complex_score': 0
        }
        
        # Check for code/section patterns
        for pattern in self.compiled_patterns:
            matches = pattern.findall(query)
            if matches:
                metadata['has_code_reference'] = True
                metadata['extracted_codes'].extend(matches if isinstance(matches[0], str) else [m[0] for m in matches])
                metadata['simple_score'] += 3  # Strong indicator of simple query
        
        # Extract section numbers
        section_numbers = re.findall(r'\b\d{3,5}\b', query)
        if section_numbers:
            metadata['extracted_sections'] = section_numbers
            metadata['simple_score'] += 2
        
        # Check for simple keywords
        simple_keyword_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query_lower)
        metadata['simple_score'] += simple_keyword_count
        
        # Check for complex keywords
        complex_keyword_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)
        metadata['complex_score'] += complex_keyword_count * 2
        
        # Query length heuristic (longer = more complex)
        if len(query.split()) > 10:
            metadata['complex_score'] += 2
        elif len(query.split()) <= 4:
            metadata['simple_score'] += 1
        
        # Check for question marks (indicates complex query)
        if '?' in query:
            metadata['complex_score'] += 2
        
        # Classification logic
        if metadata['has_code_reference'] and metadata['complex_score'] < 3:
            classification = 'simple'
            metadata['reason'] = 'Contains specific code/section reference'
        elif metadata['simple_score'] > metadata['complex_score']:
            classification = 'simple'
            metadata['reason'] = f"Simple query (score: {metadata['simple_score']} vs {metadata['complex_score']})"
        else:
            classification = 'complex'
            metadata['reason'] = f"Complex query requiring semantic understanding (score: {metadata['complex_score']} vs {metadata['simple_score']})"
        
        logger.info(f"Query classified as '{classification}': {metadata['reason']}")
        return classification, metadata
    
    def extract_code_filter(self, query: str) -> str:
        """
        Extract code filter from query (FAM, PEN, CIV, etc.).
        
        Args:
            query: User query string
        
        Returns:
            Code abbreviation or empty string
        """
        # Map of full names to abbreviations
        code_map = {
            'family': 'FAM',
            'penal': 'PEN',
            'civil': 'CIV',
            'business': 'BPC',
            'labor': 'LAB',
            'vehicle': 'VEH',
            'procedure': 'CCP'
        }
        
        query_lower = query.lower()
        
        # Check for abbreviations
        for abbr in ['FAM', 'PEN', 'CIV', 'BPC', 'LAB', 'VEH', 'CCP']:
            if abbr.lower() in query_lower or f'{abbr.lower()} ' in query_lower:
                return abbr
        
        # Check for full names
        for name, abbr in code_map.items():
            if name in query_lower:
                return abbr
        
        return ''
    
    def extract_section_number(self, query: str) -> str:
        """
        Extract section number from query.
        
        Args:
            query: User query string
        
        Returns:
            Section number or empty string
        """
        # Try to find 3-5 digit numbers
        matches = re.findall(r'\b\d{3,5}\b', query)
        return matches[0] if matches else ''

