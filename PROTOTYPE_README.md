# 🔬 Legal Codes Search - PROTOTYPE

## ⚠️ Important: This is an Independent Testing Prototype

**What this is:**
- Standalone search testing environment
- Runs on **port 8888** (separate from your main website)
- **Read-only access** to your MongoDB (no data modifications)
- Completely independent - does not affect codecond_ca website
- Can start/stop anytime without risk

**What this is NOT:**
- ❌ NOT integrated into your main website
- ❌ NOT replacing anything
- ❌ NOT modifying your MongoDB data
- ❌ NOT affecting any existing services

---

## 🚀 Quick Start (5 Minutes)

### 1. Configure MongoDB Connection

```bash
cd Architecture_design
cp env.template .env
vim .env
```

Set your MongoDB connection (read-only access is fine):
```bash
MONGODB_URL=mongodb://your-mongodb-host:27017
MONGODB_DATABASE=legal_codes
MONGODB_COLLECTION=ca_codes
```

### 2. Start the Prototype

```bash
make up
```

You'll see:
```
=========================================
PROTOTYPE SEARCH API: http://localhost:8888
Interactive Testing:  http://localhost:8888/docs
Health Check:         http://localhost:8888/health
=========================================

NOTE: This is independent prototype (port 8888)
      Your main website is unaffected
```

### 3. Sync Your Data

```bash
make sync
```

This reads your CA codes from MongoDB and builds the search indexes.
Takes ~30 minutes for 20,000 sections.

### 4. Test It!

Open in browser:
```
http://localhost:8888/docs
```

Try a search:
- Click "POST /search/hybrid"
- Click "Try it out"
- Enter: `{"query": "property rights", "limit": 10}`
- Click "Execute"

---

## 📊 Prototype URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Interactive Testing** | http://localhost:8888/docs | Main testing interface |
| **API Docs** | http://localhost:8888/redoc | Reference documentation |
| **Health Check** | http://localhost:8888/health | System status |
| **Root** | http://localhost:8888 | API info |

---

## 🎯 Testing Checklist

Use the web interface to test:

- [ ] **Keyword search**: Find exact statute codes
- [ ] **Semantic search**: Natural language queries
- [ ] **Hybrid search**: Best of both worlds
- [ ] **Speed**: Check query times (< 200ms)
- [ ] **Relevance**: Verify results match queries
- [ ] **Filtering**: Test by code_name
- [ ] **Pagination**: Try different limits

---

## 🛠️ Prototype Commands

```bash
# Start prototype
make up

# Check if it's working
make health

# Load your data
make sync

# Quick test
make test-hybrid

# Stop prototype
make down

# View logs
make logs

# Clean everything (removes data)
make clean
```

---

## 📱 Example Test Queries

Try these in the web interface (http://localhost:8888/docs):

### Exact Lookup
```json
{
  "query": "CAL-CIVIL-1234",
  "limit": 5
}
```

### Natural Language
```json
{
  "query": "what are tenant eviction rights in California?",
  "limit": 10
}
```

### Filtered Search
```json
{
  "query": "property",
  "limit": 10,
  "filters": {"code_name": "Civil Code"}
}
```

---

## 🔍 What You'll Evaluate

During prototype testing, consider:

1. **Search Quality**
   - Are results relevant?
   - Do natural language queries work?
   - Which search type (keyword/semantic/hybrid) works best?

2. **Performance**
   - Query speed (should be < 200ms)
   - System responsiveness
   - Concurrent request handling

3. **Usability**
   - Is the web interface intuitive?
   - Are results easy to understand?
   - What features are missing?

4. **Data Accuracy**
   - Do results match your MongoDB data?
   - Are statute codes correct?
   - Is content complete?

---

## 💾 Data Safety

**MongoDB Access**: Read-only
- ✅ Prototype only reads from your MongoDB
- ✅ No writes, updates, or deletes
- ✅ Your original data stays intact
- ✅ Can sync multiple times safely

**Prototype Data**: Isolated
- Search indexes stored separately in Elasticsearch/Qdrant
- Stopping prototype (`make down`) keeps search data
- `make clean` removes all prototype data
- Your MongoDB remains untouched

---

## 🐛 Troubleshooting

### Services won't start
```bash
docker-compose ps
make logs
```

### Can't connect to MongoDB
- Check connection string in `.env`
- Verify MongoDB is accessible
- Test: `docker exec -it <mongo> mongosh`

### Sync fails
```bash
make logs-sync
# Check field names match:
# - statute_code
# - title
# - content
# - code_name
```

### No search results
```bash
make health
# Verify document counts > 0
```

---

## 🚪 Stopping the Prototype

When done testing:

```bash
# Stop all services (keeps data)
make down

# Stop and remove all data
make clean
```

**Your main website and MongoDB remain completely unaffected.**

---

## 📈 Next Steps After Testing

Based on your evaluation:

✅ **If you like it:**
- Integrate into codecond_ca (see INTEGRATION_GUIDE.md)
- Deploy to production (see DEPLOYMENT.md)
- Add V2 features (hierarchical navigation, etc.)

❌ **If you don't:**
- Run `make clean`
- Delete the Architecture_design folder
- No harm done - everything isolated

---

## 💡 Remember

This is a **PROTOTYPE for TESTING**:
- Port 8888 (not 8000)
- Independent from main website
- Read-only MongoDB access
- Safe to experiment
- Easy to start/stop

**Happy Testing!** 🎉

