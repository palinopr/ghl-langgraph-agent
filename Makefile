# Makefile for LangGraph GHL Agent
# Run these commands before deploying to save time!

.PHONY: validate test deploy clean help

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