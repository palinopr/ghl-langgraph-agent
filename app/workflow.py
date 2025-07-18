"""
ENHANCED WORKFLOW - Supervisor as the Brain
This workflow now matches n8n pattern:
1. Supervisor loads full GHL context FIRST
2. Analyzes what changed
3. Updates GHL with new data
4. Routes with complete context
5. Responder sends messages
"""
# Import the enhanced workflow
from app.workflow_enhanced_supervisor import enhanced_workflow

# Export the enhanced workflow as the main workflow
workflow = enhanced_workflow

# Export for langgraph.json
__all__ = ["workflow"]