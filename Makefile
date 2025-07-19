# Makefile for LangGraph GHL Agent
# Run these commands before deploying to save time!

.PHONY: validate test deploy clean help docker-test docker-up docker-down live-test

# Default target
help:
	@echo "🤖 LangGraph GHL Agent - Development Commands"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make validate    - Quick workflow validation (5 seconds)"
	@echo "  make test        - Full pre-deployment test suite (30 seconds)"
	@echo "  make deploy      - Validate and deploy to LangGraph"
	@echo "  make clean       - Remove Python cache files"
	@echo ""
	@echo "Development:"
	@echo "  make run         - Run locally with Python 3.13"
	@echo "  make monitor     - Watch deployment logs"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-test - Test Docker setup and configuration"
	@echo "  make docker-up   - Start Docker containers"
	@echo "  make docker-down - Stop Docker containers"
	@echo "  make docker-logs - View Docker container logs"
	@echo "  make test-docker - Run tests inside Docker container"
	@echo ""
	@echo "Live Testing:"
	@echo "  make live-test   - Run comprehensive live tests"
	@echo ""

# Quick validation (run before every push)
validate:
	@echo "⚡ Running quick validation..."
	@source venv313/bin/activate && python validate_workflow.py

# Full test suite
test:
	@echo "🧪 Running full test suite..."
	@source venv313/bin/activate && python test_langgraph_deployment.py

# Run locally
run:
	@echo "🚀 Starting local server..."
	@if [ -d "venv313" ]; then \
		source venv313/bin/activate && python app.py; \
	else \
		python app.py; \
	fi

# Deploy (validates first)
deploy: validate
	@echo "🚀 Deploying to LangGraph..."
	@git push origin main

# Clean Python cache
clean:
	@echo "🧹 Cleaning Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.pyo" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .coverage .mypy_cache .ruff_cache 2>/dev/null || true
	@echo "✅ Cleaned!"

# Monitor deployment
monitor:
	@echo "📊 Opening LangSmith deployment monitor..."
	@open https://smith.langchain.com/o/*/projects/p/ghl-langgraph-agent/deployments

# Install git hooks
install-hooks:
	@echo "📎 Installing git hooks..."
	@git config core.hooksPath .githooks
	@echo "✅ Git hooks installed!"

# Docker commands
docker-test:
	@echo "🐳 Testing Docker setup..."
	@./test_docker_setup.sh

docker-up:
	@echo "🚀 Starting Docker containers..."
	@docker-compose up -d
	@echo "✅ Containers started! Check logs with: make docker-logs"

docker-down:
	@echo "🛑 Stopping Docker containers..."
	@docker-compose down
	@echo "✅ Containers stopped!"

docker-logs:
	@echo "📊 Showing Docker logs..."
	@docker-compose logs -f

test-docker:
	@echo "🧪 Running tests in Docker..."
	@./test_in_docker.sh

# Live testing
live-test:
	@echo "🔍 Running live tests..."
	@if [ -d "venv313" ]; then \
		source venv313/bin/activate && python run_live_tests.py; \
	else \
		python run_live_tests.py; \
	fi

# Build Docker image
docker-build:
	@echo "🔨 Building Docker image..."
	@docker build -t ghl-langgraph-agent:latest .
	@echo "✅ Docker image built!"