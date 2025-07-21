"""
Streaming-enabled workflow runner for real-time updates
"""
from typing import Dict, Any, AsyncIterator
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from app.workflow_optimized import create_optimized_workflow
from app.utils.simple_logger import get_logger
from app.debug.trace_collector import trace_collector

logger = get_logger("workflow_streaming")

# Create workflow with checkpointing for persistence
checkpointer = MemorySaver()
streaming_workflow = create_optimized_workflow().compile(checkpointer=checkpointer)


async def stream_workflow(
    webhook_data: Dict[str, Any],
    stream_mode: str = "updates"
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream workflow execution with real-time updates
    
    Args:
        webhook_data: Webhook data from GHL
        stream_mode: "updates" for incremental updates, "values" for full state
        
    Yields:
        Workflow updates as they happen
    """
    try:
        # Extract contact ID and message
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=message_body)],
            "contact_id": contact_id,
            "webhook_data": webhook_data,
            "extracted_data": {},
            "lead_score": 0,
            "current_agent": None,
            "should_end": False,
            "workflow_triggered": True
        }
        
        # Configuration with thread ID for conversation persistence
        config = {
            "configurable": {
                "thread_id": f"conversation_{contact_id}",
                "checkpoint_ns": "main"
            }
        }
        
        # Log streaming start
        logger.info(f"Starting streaming workflow for contact {contact_id}")
        trace_collector.add_event(contact_id, "streaming", "Starting workflow stream")
        
        # Stream the workflow
        async for chunk in streaming_workflow.astream(
            initial_state,
            config,
            stream_mode=stream_mode
        ):
            # Log each update
            for node, update in chunk.items():
                logger.debug(f"Stream update from {node}: {type(update)}")
                trace_collector.add_event(
                    contact_id, 
                    "stream_update", 
                    f"Update from {node}",
                    {"node": node, "has_messages": "messages" in update if isinstance(update, dict) else False}
                )
                
                # Yield the update
                yield {
                    "node": node,
                    "update": update,
                    "timestamp": trace_collector.get_timestamp()
                }
                
                # If this is the final message from responder, we're done
                if node == "responder" and isinstance(update, dict):
                    if update.get("should_end", False):
                        logger.info(f"Workflow completed for contact {contact_id}")
                        trace_collector.add_event(contact_id, "complete", "Workflow finished")
                        break
        
    except Exception as e:
        logger.error(f"Error in streaming workflow: {str(e)}")
        trace_collector.add_error(contact_id, "stream_error", str(e))
        yield {
            "error": str(e),
            "node": "error",
            "timestamp": trace_collector.get_timestamp()
        }


async def get_conversation_state(contact_id: str) -> Dict[str, Any]:
    """
    Get the current state of a conversation
    
    Args:
        contact_id: The contact ID to get state for
        
    Returns:
        Current conversation state
    """
    config = {
        "configurable": {
            "thread_id": f"conversation_{contact_id}",
            "checkpoint_ns": "main"
        }
    }
    
    try:
        # Get the latest checkpoint
        checkpoint = await streaming_workflow.checkpointer.aget(config)
        if checkpoint and checkpoint.channel_values:
            return checkpoint.channel_values
        return {}
    except Exception as e:
        logger.error(f"Error getting conversation state: {str(e)}")
        return {}


# Export streaming functions
__all__ = ["stream_workflow", "get_conversation_state", "streaming_workflow"]