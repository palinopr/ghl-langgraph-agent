"""
LangGraph GHL Agent Application
"""
# Import tracing first to ensure it's configured before any LangChain imports
from app.utils.tracing import setup_langsmith_tracing, is_tracing_enabled

# Setup tracing on import
if is_tracing_enabled():
    print("✓ LangSmith tracing is enabled")
else:
    print("✗ LangSmith tracing is disabled (no API key found)")

__version__ = "3.0.0"  # v3 with intelligence layer and tracing

# Note: workflow and webhook_app are imported directly where needed
# to avoid circular imports during module initialization