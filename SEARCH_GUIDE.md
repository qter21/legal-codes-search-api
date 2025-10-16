# 🔍 Search Interface Guide

## ✅ System Status

- **Total Documents**: 18,134 CA legal code sections
- **Elasticsearch**: ✅ Fully operational
- **Qdrant (Vector Search)**: ⚠️ Needs fixing (optional for now)
- **API Port**: http://localhost:8888

---

## 🌐 Interactive Web Interface

### **Best Option: Swagger UI**
Open in your browser: **http://localhost:8888/docs**

**Features:**
- Interactive "Try it out" buttons
- Auto-complete for parameters
- Real-time results
- No coding required!

**Alternative**: ReDoc at http://localhost:8888/redoc

---

## 🔍 Available Search Endpoints

### 1. **Keyword Search** (Currently Working)
**Endpoint**: `POST /search/keyword`

Traditional text search - finds exact and fuzzy matches.

**Example Request:**
```json
{
  "query": "property rights",
  "limit": 10,
  "offset": 0,
  "code_filter": ""
}
```

**Parameters:**
- `query` (required): Search terms
- `limit` (optional): Number of results (default: 10)
- `offset` (optional): Pagination offset (default: 0)
- `code_filter` (optional): Filter by code (e.g., "FAM", "PEN", "CIV")

**Example Results:**
- Query: "property rights" → 4,067 results in 94ms
- Query: "marriage" → 339 results in 16ms
- Query: "criminal" → 1,541 results in 19ms

---

### 2. **Semantic Search** (Needs Qdrant Fix)
**Endpoint**: `POST /search/semantic`

AI-powered search that understands meaning, not just keywords.

**Status**: ⚠️ Temporarily unavailable (Qdrant needs fixing)

---

### 3. **Hybrid Search** (Needs Qdrant Fix)
**Endpoint**: `POST /search/hybrid`

Combines keyword + semantic search for best results.

**Status**: ⚠️ Temporarily unavailable (Qdrant needs fixing)

---

## 📝 Quick Search Examples

### Example 1: General Search
```bash
curl -X POST http://localhost:8888/search/keyword \
  -H "Content-Type: application/json" \
  -d '{
    "query": "property rights",
    "limit": 5
  }'
```

### Example 2: Filter by Code
```bash
curl -X POST http://localhost:8888/search/keyword \
  -H "Content-Type: application/json" \
  -d '{
    "query": "criminal offense",
    "limit": 5,
    "code_filter": "PEN"
  }'
```

### Example 3: Pagination
```bash
curl -X POST http://localhost:8888/search/keyword \
  -H "Content-Type: application/json" \
  -d '{
    "query": "marriage",
    "limit": 10,
    "offset": 10
  }'
```

---

## 📊 Sample Results

```json
{
  "success": true,
  "results": [
    {
      "document_id": "68e6bc8beaa3782a119387f7",
      "statute_code": "",
      "title": "",
      "section": "1500",
      "content": "The property rights of spouses prescribed by statute...",
      "score": 24.91,
      "source": "keyword"
    }
  ],
  "metadata": {
    "total_results": 4067,
    "returned_results": 3,
    "query_time_ms": 94.05,
    "search_type": "keyword"
  }
}
```

---

## 🎯 Common Use Cases

### Legal Research
```
Query: "breach of contract"
Query: "negligence liability"
Query: "property damage"
```

### Family Law
```
Query: "child custody"
Query: "divorce proceedings"
Query: "spousal support"
```

### Criminal Law
```
Query: "assault battery"
Query: "theft robbery"
Query: "criminal intent"
```

### Business Law
```
Query: "corporate governance"
Query: "partnership agreement"
Query: "commercial transactions"
```

---

## 🏥 Health Check

Check system status:
```bash
curl http://localhost:8888/health | python3 -m json.tool
```

Expected response:
```json
{
  "status": "healthy",
  "elasticsearch": {
    "connected": true,
    "document_count": 18134
  }
}
```

---

## 🐛 Known Issues

### Qdrant Vector Search Error
**Issue**: Format error when indexing vectors  
**Impact**: Semantic and Hybrid search unavailable  
**Workaround**: Use Keyword search (fully functional)  
**Fix**: Coming soon

---

## 💡 Tips

1. **Start Simple**: Use Keyword search to get familiar with the data
2. **Use Filters**: Add `code_filter` to narrow results by legal code
3. **Try Different Terms**: Legal terminology may differ from common language
4. **Paginate Large Results**: Use `offset` and `limit` for better performance
5. **Check Scores**: Higher scores = more relevant results

---

## 📚 Legal Code Abbreviations

Common codes in the database:
- **FAM**: Family Code
- **PEN**: Penal Code
- **CIV**: Civil Code
- **CCP**: Code of Civil Procedure
- **BPC**: Business and Professions Code
- **LAB**: Labor Code
- **VEH**: Vehicle Code
- **WIC**: Welfare and Institutions Code

---

## 🚀 Next Steps

1. **Test the Web Interface**: Open http://localhost:8888/docs
2. **Try Sample Searches**: Use examples above
3. **Fix Qdrant** (Optional): Enable semantic search
4. **Customize**: Add filters, adjust limits, etc.

---

**Questions?** Check the logs with: `docker-compose logs search-api`

