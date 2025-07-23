"""LangGraph workflow export for deployment"""
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the workflow from the app module
from app.workflow import workflow as graph

# Export the graph for LangGraph Platform
__all__ = ["graph"]