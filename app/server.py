"""
LangGraph API Server Entry Point
This file is loaded by LangGraph deployment
"""
from app.workflow import workflow

# Export workflow for LangGraph API
graph = workflow

# Also export as 'agent' which is what langgraph.json references
agent = workflow

__all__ = ["graph", "agent", "workflow"]