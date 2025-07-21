"""
MEMORY-OPTIMIZED WORKFLOW - Intelligent Context Management
Flow: Webhook → Memory-Aware Receptionist → Intelligence → Memory-Aware Supervisor → Agent → Responder

Key Improvements:
1. Memory isolation per agent (no context confusion)
2. Sliding window memory (last 6-10 messages only)
3. Clean handoffs between agents
4. Separation of historical vs current messages
5. Agent-specific context filtering

This implements the MEMORY-OPTIMIZED flow pattern where:
- Each agent has isolated memory space
- Historical messages are summarized, not loaded fully
- Handoffs include minimal context transfer
- No agent sees irrelevant messages from others
"""
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from app.workflow_memory_optimized import memory_optimized_workflow
from app.debug.trace_middleware import inject_trace_id
from app.utils.simple_logger import get_logger

logger = get_logger("workflow")

# Export as main workflow
workflow = memory_optimized_workflow


async def run_workflow(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the workflow with webhook data
    
    Args:
        webhook_data: Webhook data from GHL
        
    Returns:
        Workflow result
    """
    try:
        # Extract contact ID, message, and thread ID
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        thread_id = webhook_data.get("conversationId") or webhook_data.get("threadId")
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=message_body)],
            "contact_id": contact_id,
            "thread_id": thread_id,  # Add thread ID for conversation filtering
            "webhook_data": webhook_data,
            "extracted_data": {},
            "lead_score": 0,
            "should_end": False,
            "routing_attempts": 0
        }
        
        # Inject trace ID if available from request context
        if hasattr(webhook_data, "__trace_id__"):
            initial_state = inject_trace_id(initial_state, webhook_data.__trace_id__)
        
        # Run the workflow
        logger.info(f"Running workflow for contact {contact_id}")
        result = await workflow.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": contact_id}}
        )
        
        logger.info(f"Workflow completed for contact {contact_id}")
        return {
            "success": True,
            "contact_id": contact_id,
            "message_sent": result.get("message_sent", False),
            "final_state": result
        }
        
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "contact_id": webhook_data.get("contactId", "unknown")
        }


# Export for langgraph.json and imports
__all__ = ["workflow", "run_workflow"]