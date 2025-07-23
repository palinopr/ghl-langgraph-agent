"""
Enhanced Thread ID Mapper Node
Attempts to override LangGraph Cloud's checkpoint configuration
"""
from typing import Dict, Any, Optional
from app.utils.simple_logger import get_logger
import copy

logger = get_logger("thread_id_mapper")


async def thread_id_mapper_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced mapper that attempts to override checkpoint configuration
    to force LangGraph Cloud to use our consistent thread_ids
    """
    logger.info("=== ENHANCED THREAD ID MAPPER STARTING ===")
    logger.info(f"State keys: {list(state.keys())}")
    
    # Extract identifiers from various possible locations
    contact_id = (
        state.get("contact_id") or
        state.get("contactId") or
        state.get("webhook_data", {}).get("contactId") or
        state.get("webhook_data", {}).get("id")
    )
    
    conversation_id = (
        state.get("conversationId") or
        state.get("conversation_id") or  
        state.get("webhook_data", {}).get("conversationId")
    )
    
    # Log what we found
    logger.info(f"Contact ID: {contact_id}")
    logger.info(f"Conversation ID: {conversation_id}")
    logger.info(f"Current thread_id in state: {state.get('thread_id')}")
    
    # Check for config
    if "__config__" in state:
        logger.info(f"Config found: {state['__config__']}")
        if "configurable" in state["__config__"]:
            logger.info(f"Configurable: {state['__config__']['configurable']}")
    
    # Generate our consistent thread_id
    if conversation_id:
        new_thread_id = f"conv-{conversation_id}"
        logger.info(f"Using conversationId-based thread: {new_thread_id}")
    elif contact_id:
        new_thread_id = f"contact-{contact_id}"
        logger.info(f"Using contact-based thread: {new_thread_id}")
    else:
        # Critical error - no identifiers
        logger.error("❌ CRITICAL: No contact_id or conversation_id found!")
        logger.error(f"webhook_data: {state.get('webhook_data', {})}")
        # Try to extract from the original thread_id if it contains contact info
        original_thread_id = state.get("thread_id", "")
        if "contact-" in original_thread_id:
            new_thread_id = original_thread_id
            logger.info(f"Reusing existing contact-based thread_id: {new_thread_id}")
        else:
            new_thread_id = f"fallback-{original_thread_id[:8]}"
            logger.warning(f"Using fallback thread_id: {new_thread_id}")
    
    # Preserve original thread_id
    original_thread_id = state.get("thread_id", "no-original-thread-id")
    
    # Create updated state
    updated_state = copy.deepcopy(state)  # Deep copy to avoid mutations
    
    # Update thread IDs in state
    updated_state["thread_id"] = new_thread_id
    updated_state["mapped_thread_id"] = new_thread_id
    updated_state["original_thread_id"] = original_thread_id
    
    # Ensure identifiers are in state
    if contact_id:
        updated_state["contact_id"] = contact_id
    if conversation_id:
        updated_state["conversation_id"] = conversation_id
    
    # CRITICAL: Attempt to override checkpoint configuration
    config_updated = False
    if "__config__" in updated_state:
        # Deep copy the config to avoid mutations
        updated_state["__config__"] = copy.deepcopy(updated_state["__config__"])
        
        # Ensure configurable exists
        if "configurable" not in updated_state["__config__"]:
            updated_state["__config__"]["configurable"] = {}
        
        # Override the thread_id in config
        old_config_thread = updated_state["__config__"]["configurable"].get("thread_id", "none")
        updated_state["__config__"]["configurable"]["thread_id"] = new_thread_id
        config_updated = True
        
        logger.info(f"✅ CRITICAL: Overrode config thread_id: {old_config_thread} → {new_thread_id}")
        logger.info(f"Updated config: {updated_state['__config__']['configurable']}")
    else:
        logger.warning("⚠️ No __config__ found in state - cannot override checkpoint config")
        # Try to inject config
        updated_state["__config__"] = {
            "configurable": {
                "thread_id": new_thread_id
            }
        }
        logger.info(f"Injected new config with thread_id: {new_thread_id}")
    
    # Log the mapping result
    logger.info(f"✅ Thread ID mapping complete:")
    logger.info(f"   Original: {original_thread_id}")
    logger.info(f"   Mapped to: {new_thread_id}")
    logger.info(f"   Config updated: {config_updated}")
    
    # Try to manually load checkpoint with our thread_id
    # This is a last-ditch effort to ensure we have conversation history
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        import os
        
        checkpoint_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints.db")
        if os.path.exists(checkpoint_db):
            logger.info(f"Attempting to load checkpoint from: {checkpoint_db}")
            
            async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as checkpointer:
                checkpoint_config = {"configurable": {"thread_id": new_thread_id}}
                checkpoint_tuple = await checkpointer.aget(checkpoint_config)
                
                if checkpoint_tuple and checkpoint_tuple.checkpoint:
                    checkpoint_data = checkpoint_tuple.checkpoint.get("channel_values", {})
                    
                    # Load messages if not already present
                    if "messages" in checkpoint_data and not updated_state.get("messages"):
                        updated_state["messages"] = checkpoint_data["messages"]
                        logger.info(f"✅ Loaded {len(checkpoint_data['messages'])} messages from checkpoint")
                    
                    # Load extracted data
                    if "extracted_data" in checkpoint_data:
                        updated_state["extracted_data"] = checkpoint_data["extracted_data"]
                        logger.info(f"✅ Loaded extracted data: {checkpoint_data['extracted_data']}")
                    
                    # Load other important fields
                    for field in ["lead_score", "score_history", "last_agent", "conversation_stage"]:
                        if field in checkpoint_data:
                            updated_state[field] = checkpoint_data[field]
                            logger.info(f"✅ Loaded {field}: {checkpoint_data[field]}")
                else:
                    logger.info(f"No checkpoint found for thread: {new_thread_id}")
        else:
            logger.warning(f"Checkpoint database not found at: {checkpoint_db}")
            
    except Exception as e:
        logger.warning(f"Could not manually load checkpoint: {e}")
    
    logger.info("=== ENHANCED THREAD ID MAPPER COMPLETE ===")
    
    return updated_state


# Export
__all__ = ["thread_id_mapper_node"]