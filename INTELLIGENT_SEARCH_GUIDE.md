# 🧠 Intelligent Search with LLM + RAG

**Status**: ✅ Fully Operational  
**Date**: October 16, 2025

---

## Overview

The intelligent search system automatically routes queries based on complexity:

1. **Simple Queries** → Fast keyword search (Elasticsearch)
2. **Complex Queries** → RAG (Retrieval-Augmented Generation) with semantic search

---

## How It Works

### 1. Query Classification

The system analyzes your query and classifies it:

**Simple Query Indicators:**
- Specific code/section references: "FAM 3044", "Section 3044"
- Code abbreviations: FAM, PEN, CIV, BPC, LAB, VEH, CCP
- Short, direct lookups: "Family Code 3044"
- Keywords: "section", "code", "statute", "what is", "define"

**Complex Query Indicators:**
- Question words: "how", "why", "when", "what are"
- Semantic questions: "explain", "describe", "compare"
- Long queries (10+ words)
- Contains "?"
- Example: "What are parental rights after divorce in California?"

### 2. Routing Logic

```
Query → Classifier → Route

Simple:  "FAM 3044"
         ↓
         Keyword Search (Fast, Exact)
         ↓
         Results

Complex: "What are parental rights after divorce?"
         ↓
         RAG Service
         ↓
         Semantic Search + Context Building
         ↓
         Structured Answer + Results
```

---

## API Endpoints

### Intelligent Search
`POST /intelligent/search`

Automatically routes queries to the best search method.

**Request:**
```json
{
  "query": "What are parental rights after divorce?",
  "limit": 5,
  "force_mode": null  // Optional: "simple" or "complex"
}
```

**Response:**
```json
{
  "query": "...",
  "classification": "simple" | "complex",
  "classification_reason": "...",
  "search_mode": "keyword" | "rag",
  "results": [...],
  "metadata": {...},
  "rag_context": {  // Only for complex queries
    "summary": "...",
    "relevant_sections": [...],
    "context_used": 5
  }
}
```

### Query Classification
`POST /intelligent/classify?query=...`

Test query classification without performing search.

**Request:**
```
POST /intelligent/classify?query=family+code+3044
```

**Response:**
```json
{
  "query": "family code 3044",
  "classification": "simple",
  "metadata": {
    "has_code_reference": true,
    "extracted_codes": ["family"],
    "extracted_sections": ["3044"],
    "simple_score": 6,
    "complex_score": 0,
    "reason": "Contains specific code/section reference"
  },
  "recommended_search_mode": "keyword"
}
```

---

## Usage Examples

### Example 1: Simple Lookup
```bash
curl -X POST http://localhost:8888/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "FAM 3044",
    "limit": 3
  }'
```

**Result:**
- Classification: `simple`
- Search Mode: `keyword`
- Speed: ~10ms
- Directly returns FAM Section 3044

### Example 2: Complex Question
```bash
curl -X POST http://localhost:8888/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are parental rights after divorce in California?",
    "limit": 5
  }'
```

**Result:**
- Classification: `complex`
- Search Mode: `rag`
- Speed: ~50-100ms
- Returns:
  - Summary answer
  - Relevant sections (FAM 3040-3048)
  - Context used
  - Full results

### Example 3: Force Search Mode
```bash
curl -X POST http://localhost:8888/intelligent/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "FAM 3044",
    "limit": 3,
    "force_mode": "complex"  // Force RAG mode
  }'
```

---

## Classification Examples

| Query | Classification | Reason |
|-------|----------------|--------|
| "FAM 3044" | Simple | Contains code/section reference |
| "Family Code Section 3044" | Simple | Specific section lookup |
| "Section 3044" | Simple | Direct section reference |
| "What are parental rights?" | Complex | Question, no specific section |
| "How does custody work in California?" | Complex | Question, semantic understanding needed |
| "Explain domestic violence laws" | Complex | Requires explanation |
| "Compare FAM 3040 and FAM 3044" | Complex | Comparison requires understanding |
| "3044" | Simple | Section number |

---

## RAG (Retrieval-Augmented Generation)

For complex queries, the RAG service:

1. **Retrieves** relevant documents using hybrid search (keyword + semantic)
2. **Builds context** from top 3-5 most relevant sections
3. **Generates** structured answer with:
   - Summary
   - Relevant sections
   - Full results

### Current RAG Capabilities

**V1 (Current):**
- ✅ Hybrid retrieval (keyword + semantic)
- ✅ Context building
- ✅ Template-based summaries
- ✅ Relevance ranking

**V2 (Future with LLM):**
- 🔄 Natural language generation
- 🔄 Follow-up questions
- 🔄 Multi-turn conversations
- 🔄 Citation generation
- 🔄 Legal interpretation

---

## Integration with Docker Model Runner

To enhance RAG with actual LLM generation:

### Step 1: Add LLM Model
```bash
# Pull a legal-focused LLM
docker model pull ai/llama3-legal

# Or use general purpose
docker model pull ai/llama3
```

### Step 2: Update RAG Service
Modify `search-api/services/rag_service.py`:

```python
def _generate_summary(self, query: str, documents: List[Dict]) -> str:
    """Generate summary using LLM."""
    
    # Build context
    context = self._build_context(documents)
    
    # Create prompt
    prompt = f"""
    Based on the following California legal code sections, answer this question:
    
    Question: {query}
    
    Relevant Sections:
    {context}
    
    Please provide a clear, accurate answer based on these sections.
    """
    
    # Call Docker Model Runner API
    response = requests.post(
        "http://localhost:8080/v1/chat/completions",
        json={
            "model": "ai/llama3-legal",
            "messages": [
                {"role": "system", "content": "You are a legal assistant expert in California law."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }
    )
    
    return response.json()["choices"][0]["message"]["content"]
```

---

## Performance

| Search Mode | Speed | Use Case |
|-------------|-------|----------|
| Simple (Keyword) | ~10-20ms | Specific code lookups |
| Complex (RAG) | ~50-100ms | Semantic questions |
| Complex (RAG + LLM) | ~500-1000ms | With generation |

---

## Web Interface

The search interface at `http://localhost:8888/` automatically uses intelligent search.

**Features:**
- Automatically classifies queries
- Shows classification reason
- Displays appropriate results
- Highlights context for complex queries

---

## Best Practices

### For Simple Queries:
- Use specific code/section numbers
- Include code abbreviations (FAM, PEN, etc.)
- Keep queries short and direct

### For Complex Queries:
- Ask natural questions
- Use complete sentences
- Include context about your situation
- Use question words (what, how, why)

### Examples:

**Good Simple:**
- ✅ "FAM 3044"
- ✅ "Family Code Section 3044"
- ✅ "Section 3044"

**Good Complex:**
- ✅ "What are parental rights after divorce?"
- ✅ "How does joint custody work in California?"
- ✅ "Explain domestic violence presumptions in custody cases"

**Avoid:**
- ❌ "3044 parental" (ambiguous)
- ❌ "rights" (too vague)

---

## Troubleshooting

### Query classified incorrectly?

Use `force_mode` to override:
```json
{
  "query": "...",
  "force_mode": "simple"  // or "complex"
}
```

### Want to see classification details?

Use the classify endpoint:
```bash
curl "http://localhost:8888/intelligent/classify?query=your+query+here"
```

### Slow responses?

- Simple queries should be < 20ms
- Complex queries 50-100ms
- If slower, check:
  - Qdrant connection
  - Embedding model loading
  - Network latency

---

## Future Enhancements

1. **True LLM Integration**
   - Natural language generation
   - Multi-turn conversations
   - Follow-up questions

2. **Learning System**
   - Learn from query patterns
   - Improve classification over time
   - Personalized results

3. **Advanced RAG**
   - Multi-document synthesis
   - Legal reasoning
   - Citation generation
   - Precedent analysis

4. **Specialized Models**
   - Legal-specific embeddings
   - Domain-specific LLMs
   - Fine-tuned classifiers

---

**Status**: Production Ready for Prototype
**Last Updated**: October 16, 2025

Enjoy your intelligent search system! 🚀

