.PHONY: help build up down logs clean test sync health

help:
	@echo "Legal Codes Search Architecture - Make Commands"
	@echo ""
	@echo "  make build      - Build all Docker images"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make sync       - Run sync job to populate search engines"
	@echo "  make sync-full  - Run full sync (re-index all data)"
	@echo "  make health     - Check API health status"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Remove containers, volumes, and generated files"
	@echo ""

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Services starting..."
	@echo "========================================="
	@echo "PROTOTYPE SEARCH API: http://localhost:8888"
	@echo "Interactive Testing:  http://localhost:8888/docs"
	@echo "Health Check:         http://localhost:8888/health"
	@echo "========================================="
	@echo "Elasticsearch at http://localhost:9200"
	@echo "Qdrant at http://localhost:6333"
	@echo ""
	@echo "NOTE: This is independent prototype (port 8888)"
	@echo "      Your main website is unaffected"

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f search-api

logs-sync:
	docker-compose logs -f sync-service

sync:
	docker-compose run --rm sync-service python sync_job.py

sync-full:
	docker-compose run --rm -e SYNC_MODE=full sync-service python sync_job.py

health:
	@echo "Checking prototype search API health (port 8888)..."
	@curl -s http://localhost:8888/health | python -m json.tool

test-api:
	cd search-api && pytest tests/ -v

test-sync:
	cd sync-service && pytest tests/ -v

test: test-api test-sync

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf sync-service/logs/*
	rm -rf search-api/logs/*

# Development commands
dev-api:
	cd search-api && python main.py

dev-sync:
	cd sync-service && python sync_job.py

install-api:
	cd search-api && pip install -r requirements.txt

install-sync:
	cd sync-service && pip install -r requirements.txt

install: install-api install-sync

# Quick test queries (Prototype on port 8888)
test-keyword:
	@echo "Testing keyword search on prototype (port 8888)..."
	@curl -s -X POST http://localhost:8888/search/keyword \
		-H "Content-Type: application/json" \
		-d '{"query": "civil code property", "limit": 5}' | python -m json.tool

test-semantic:
	@echo "Testing semantic search on prototype (port 8888)..."
	@curl -s -X POST http://localhost:8888/search/semantic \
		-H "Content-Type: application/json" \
		-d '{"query": "property ownership rights", "limit": 5}' | python -m json.tool

test-hybrid:
	@echo "Testing hybrid search on prototype (port 8888)..."
	@curl -s -X POST http://localhost:8888/search/hybrid \
		-H "Content-Type: application/json" \
		-d '{"query": "property rights", "limit": 5}' | python -m json.tool

