"""
LINEAR WORKFLOW - No Circular Agent Transfers
Flow: Webhook → Receptionist → Supervisor Brain → Agent → Responder

Key Changes:
1. Agents CANNOT transfer to each other (no more loops!)
2. Agents can ONLY escalate back to supervisor
3. Supervisor makes ALL routing decisions (like n8n)
4. Maximum 2 routing attempts to prevent infinite loops

This implements the LINEAR flow pattern from n8n where:
- One central routing decision (supervisor)
- No agent-to-agent transfers
- Clear, predictable flow
"""
# Import the LINEAR workflow (not circular!)
from app.workflow_linear import linear_workflow

# Export as main workflow
workflow = linear_workflow

# Export for langgraph.json
__all__ = ["workflow"]