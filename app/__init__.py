"""
LangGraph GHL Agent Application
"""
# Import tracing first to ensure it's configured before any LangChain imports
from app.utils.tracing import setup_langsmith_tracing, is_tracing_enabled

# Setup tracing on import
if is_tracing_enabled():
    print(" LangSmith tracing is enabled")
else:
    print("   LangSmith tracing is disabled (no API key found)")

# Import main components
from app.workflow import workflow, create_workflow, run_workflow
from app.api.webhook import app as webhook_app

__version__ = "3.0.0"  # v3 with intelligence layer and tracing

__all__ = [
    "workflow",
    "create_workflow", 
    "run_workflow",
    "webhook_app",
    "__version__"
]