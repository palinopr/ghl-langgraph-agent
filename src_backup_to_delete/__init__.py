"""
LangGraph GHL Agent Application
"""
# Import tracing first to ensure it's configured before any LangChain imports
from app.utils.tracing import setup_langsmith_tracing, is_tracing_enabled
from app.utils.simple_logger import get_logger

logger = get_logger(__name__)

# Setup tracing on import
if is_tracing_enabled():
    logger.info("LangSmith tracing enabled", status="enabled", tracing_type="langsmith")
else:
    logger.warning("LangSmith tracing disabled", status="disabled", reason="no_api_key")

__version__ = "3.0.0"  # v3 with intelligence layer and tracing

# Note: workflow and webhook_app are imported directly where needed
# to avoid circular imports during module initialization