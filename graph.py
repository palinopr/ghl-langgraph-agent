"""
Root level graph entry point for LangGraph deployment
"""
# Import the main workflow with run_workflow function
from app.workflow import workflow, run_workflow

# Export as 'agent' which is what langgraph.json expects
agent = workflow

# Also export as graph for compatibility
graph = workflow

# Export run_workflow so webhook can call it
__all__ = ["agent", "graph", "workflow", "run_workflow"]