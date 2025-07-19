"""
COMPLETE WORKFLOW - Consolidated Supervisor Brain Pattern
Flow: Webhook → Receptionist → Supervisor Brain → Agent → Responder

1. Receptionist loads all GHL data (like n8n's Get Contact)
2. Supervisor Brain does EVERYTHING:
   - Analyzes and scores lead
   - Updates GHL (score, tags, fields, notes)
   - Routes to appropriate agent
3. Agents handle conversation
4. Responder sends messages
"""
# Import the supervisor brain workflow
from app.workflow_supervisor_brain import supervisor_brain_workflow

# Export as main workflow
workflow = supervisor_brain_workflow

# Export for langgraph.json
__all__ = ["workflow"]