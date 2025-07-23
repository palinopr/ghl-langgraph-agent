"""FastAPI app export for LangGraph Platform HTTP serving"""
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the FastAPI app from the webhook module
from app.api.webhook_simple import app

# Configure observability BEFORE route registration
from src.observability import configure

configure(app)

# Export the app for LangGraph Platform
__all__ = ["app"]
