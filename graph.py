"""
Root level graph entry point for LangGraph deployment
"""
# Import the FIXED workflow with run_workflow function
from app.workflow_fixed_final import workflow, run_workflow

# Export as 'agent' which is what langgraph.json expects
agent = workflow

# Also export as graph for compatibility
graph = workflow

# CRITICAL: Export run_workflow so webhook can call it!
__all__ = ["agent", "graph", "workflow", "run_workflow"]