"""
Proper Webhook Handler for LangGraph Platform
Receives ONLY the basic webhook data and processes it correctly
"""
from typing import Dict, Any
from datetime import datetime
from langchain_core.messages import HumanMessage
from app.workflow_supervisor_brain import supervisor_brain_workflow
from app.utils.simple_logger import get_logger
from app.utils.workflow_tracker import can_start_workflow, end_workflow

logger = get_logger("webhook_handler")


def parse_langgraph_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the LangGraph platform webhook format
    
    Expected format:
    {
        "assistant_id": "agent",
        "input": {
            "messages": [{"role": "user", "content": "message text"}],
            "contact_id": "{{contact.id}}",
            "contact_name": "{{contact.name}}", 
            "contact_email": "{{contact.email}}",
            "contact_phone": "{{contact.phone}}"
        },
        "stream_mode": "updates"
    }
    """
    # Extract the input data
    input_data = webhook_data.get("input", {})
    
    # Get the message from the messages array
    messages = input_data.get("messages", [])
    message_text = ""
    if messages and len(messages) > 0:
        message_text = messages[0].get("content", "")
    
    # Build simple webhook data - ONLY what GHL sends
    return {
        "id": input_data.get("contact_id", ""),
        "name": input_data.get("contact_name", ""),
        "email": input_data.get("contact_email", ""),
        "phone": input_data.get("contact_phone", ""),
        "message": message_text,
        "webhook_received_at": datetime.now().isoformat()
    }


async def handle_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle incoming webhook with proper workflow
    
    Args:
        webhook_data: Raw webhook data from LangGraph platform
        
    Returns:
        Processing result
    """
    try:
        # Parse webhook to get simple data
        simple_data = parse_langgraph_webhook(webhook_data)
        contact_id = simple_data.get("id", "unknown")
        
        logger.info(f"Processing webhook for contact {contact_id}")
        logger.info(f"Message: {simple_data.get('message', '')[:100]}...")
        
        # Check if workflow already running
        if not await can_start_workflow(contact_id):
            logger.warning(f"Workflow already running for {contact_id}, skipping")
            return {
                "status": "skipped",
                "reason": "workflow_already_running"
            }
        
        try:
            # Create minimal initial state - receptionist will load everything else
            initial_state = {
                "messages": [HumanMessage(content=simple_data["message"])],
                "contact_id": contact_id,
                "contact_name": simple_data.get("name"),
                "contact_email": simple_data.get("email"),
                "contact_phone": simple_data.get("phone"),
                "webhook_data": simple_data,
                
                # Required fields with defaults
                "interaction_count": 0,
                "should_end": False,
                "remaining_steps": 10,
                "data_loaded": False,
                "receptionist_complete": False,
                "supervisor_complete": False,
                "next_agent": None,
                "messages_sent_count": 0,
                "messages_failed_count": 0,
                "failed_messages": [],
                
                # Fields that receptionist will populate
                "contact_info": {},
                "previous_custom_fields": {},
                "conversation_history": []
            }
            
            # Configure workflow - use same thread_id for same contact
            config = {
                "configurable": {
                    "thread_id": contact_id  # Use contact_id as thread_id for continuity
                },
                "metadata": {
                    "contact_id": contact_id,
                    "source": "webhook"
                }
            }
            
            # Run workflow - receptionist will load all GHL data
            logger.info(f"Starting workflow for {contact_id}")
            result = await supervisor_brain_workflow.ainvoke(
                initial_state,
                config=config
            )
            
            # Log results
            messages_sent = result.get("messages_sent_count", 0)
            logger.info(f"Workflow completed: {messages_sent} messages sent")
            
            return {
                "status": "success",
                "contact_id": contact_id,
                "messages_sent": messages_sent,
                "agent_used": result.get("current_agent"),
                "lead_score": result.get("lead_score", 0)
            }
            
        finally:
            # Always end workflow tracking
            await end_workflow(contact_id)
            
    except Exception as e:
        logger.error(f"Webhook handling error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


# For LangGraph platform
async def agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for LangGraph platform
    This is what gets called when the webhook is received
    """
    # The state contains the webhook data
    result = await handle_webhook(state)
    
    # Return the result as part of the state
    return {
        "webhook_result": result
    }