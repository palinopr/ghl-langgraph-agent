"""
Root level graph entry point for LangGraph deployment
"""
# Import the fixed workflow
from app.workflow import workflow

# Export as 'agent' which is what langgraph.json expects
agent = workflow

# Also export as graph for compatibility
graph = workflow

__all__ = ["agent", "graph", "workflow"]