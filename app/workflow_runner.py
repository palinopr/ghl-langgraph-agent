"""
Centralized Workflow Runner with Deduplication
Ensures only one workflow runs per contact at a time
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from app.utils.simple_logger import get_logger
from app.utils.workflow_tracker import can_start_workflow, end_workflow
from app.state.conversation_state import create_initial_state
from app.workflow_supervisor_brain import supervisor_brain_workflow
from app.tools.webhook_enricher import enrich_webhook_data
from app.tools.conversation_loader import load_conversation_history

logger = get_logger("workflow_runner")


async def run_workflow_safe(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run workflow with safety checks to prevent duplicates and loops.
    
    Args:
        webhook_data: Webhook data from GHL
        
    Returns:
        Workflow result or error
    """
    contact_id = webhook_data.get("id", "unknown")
    
    # Check if workflow already running for this contact
    if not await can_start_workflow(contact_id):
        logger.warning(f"Workflow already running for contact {contact_id}, skipping")
        return {
            "status": "skipped",
            "reason": "workflow_already_running",
            "contact_id": contact_id
        }
    
    try:
        # Start timing
        start_time = datetime.now()
        
        # Enrich webhook data with full context
        logger.info(f"Enriching webhook data for contact {contact_id}")
        enriched_data = await enrich_webhook_data(webhook_data)
        
        # Create initial state
        initial_state = create_initial_state(enriched_data)
        
        # Load conversation history
        logger.info(f"Loading conversation history for contact {contact_id}")
        history = await load_conversation_history(contact_id)
        if history:
            # Prepend history to messages
            initial_state["messages"] = history + initial_state["messages"]
            logger.info(f"Loaded {len(history)} historical messages")
        
        # Add safety limits
        initial_state["interaction_count"] = 0
        initial_state["max_interactions"] = 3
        initial_state["workflow_start_time"] = start_time.isoformat()
        
        # Generate thread ID for this conversation
        thread_id = f"{contact_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Configure workflow
        config = {
            "configurable": {
                "thread_id": thread_id
            },
            "metadata": {
                "contact_id": contact_id,
                "workflow_run_id": str(uuid.uuid4()),
                "source": "webhook"
            },
            "tags": ["production", "webhook", "safe_runner"]
        }
        
        # Run workflow
        logger.info(f"Starting workflow for contact {contact_id} with thread {thread_id}")
        
        # Use the supervisor brain workflow
        result = await supervisor_brain_workflow.ainvoke(
            initial_state,
            config=config
        )
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Log completion
        logger.info(
            f"Workflow completed for contact {contact_id} in {duration:.1f}s, "
            f"interactions: {result.get('interaction_count', 0)}"
        )
        
        # Check for successful message sending
        messages_sent = result.get("messages_sent_count", 0)
        messages_failed = result.get("messages_failed_count", 0)
        
        return {
            "status": "completed",
            "contact_id": contact_id,
            "duration_seconds": duration,
            "interactions": result.get("interaction_count", 0),
            "messages_sent": messages_sent,
            "messages_failed": messages_failed,
            "agent_used": result.get("current_agent"),
            "lead_score": result.get("lead_score", 0)
        }
        
    except Exception as e:
        logger.error(f"Workflow error for contact {contact_id}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "contact_id": contact_id,
            "error": str(e)
        }
        
    finally:
        # Always mark workflow as ended
        await end_workflow(contact_id)


async def get_workflow_status(contact_id: str) -> Dict[str, Any]:
    """Check if a workflow is currently running for a contact"""
    from app.utils.workflow_tracker import is_workflow_active
    
    is_active = await is_workflow_active(contact_id)
    return {
        "contact_id": contact_id,
        "workflow_active": is_active
    }