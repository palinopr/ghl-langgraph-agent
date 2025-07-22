"""
Thread ID Mapper Node
Maps LangGraph Cloud's UUID thread_ids to our consistent pattern
This ensures conversation persistence across messages
"""
from typing import Dict, Any
from app.utils.simple_logger import get_logger
from langgraph.checkpoint.base import BaseCheckpointSaver
import asyncio

logger = get_logger("thread_id_mapper")


async def thread_id_mapper_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps thread_id to our consistent pattern based on contact/conversation
    
    This node runs FIRST and ensures we use consistent thread_ids
    for checkpoint persistence, regardless of what LangGraph Cloud provides.
    """
    logger.info("=== THREAD ID MAPPER STARTING ===")
    
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
    
    # Generate our consistent thread_id
    if conversation_id:
        new_thread_id = f"conv-{conversation_id}"
        logger.info(f"Using conversationId-based thread: {new_thread_id}")
    elif contact_id:
        new_thread_id = f"contact-{contact_id}"
        logger.info(f"Using contact-based thread: {new_thread_id}")
    else:
        # Fallback to existing if we can't determine
        new_thread_id = state.get("thread_id", "unknown")
        logger.warning(f"No identifiers found, using fallback: {new_thread_id}")
    
    # Safety check: Ensure we have valid identifiers
    if not contact_id and not conversation_id:
        logger.error("❌ CRITICAL: No contact_id or conversation_id found in state!")
        logger.error(f"State keys: {list(state.keys())}")
        # Use a fallback but log the issue prominently
        new_thread_id = state.get("thread_id", f"fallback-{state.get('original_thread_id', 'unknown')}")
        logger.warning(f"Using fallback thread_id: {new_thread_id}")
    
    # Preserve original thread_id BEFORE updating
    original_thread_id = state.get("thread_id", "no-original-thread-id")
    
    # CRITICAL: Update the thread_id in state while preserving everything else
    updated_state = {
        **state,  # Preserve ALL existing state
        "thread_id": new_thread_id,
        "mapped_thread_id": new_thread_id,  # Keep track that we mapped it
        "original_thread_id": original_thread_id  # Preserve original
    }
    
    # Also ensure contact_id is in state for downstream nodes
    if contact_id:
        updated_state["contact_id"] = contact_id
    if conversation_id:
        updated_state["conversation_id"] = conversation_id
    
    logger.info(f"✅ Thread ID mapped: {original_thread_id} → {new_thread_id}")
    
    # Try to load checkpoint with our thread_id
    try:
        # Access the checkpointer through the runtime config
        config = state.get("__config__", {})
        if config and "checkpointer" in config.get("configurable", {}):
            checkpointer = config["configurable"]["checkpointer"]
            
            # Try to get checkpoint with our thread_id
            checkpoint_config = {
                "configurable": {"thread_id": new_thread_id}
            }
            
            checkpoint = await checkpointer.aget(checkpoint_config)
            if checkpoint:
                logger.info(f"✅ Found existing checkpoint for thread: {new_thread_id}")
                # Merge checkpoint state into current state
                if checkpoint.checkpoint and "channel_values" in checkpoint.checkpoint:
                    channel_values = checkpoint.checkpoint["channel_values"]
                    # Preserve messages and other data from checkpoint
                    if "messages" in channel_values:
                        updated_state["messages"] = channel_values["messages"]
                        logger.info(f"Loaded {len(channel_values['messages'])} messages from checkpoint")
                    if "extracted_data" in channel_values:
                        updated_state["extracted_data"] = channel_values["extracted_data"]
                        logger.info(f"Loaded extracted data: {channel_values['extracted_data']}")
            else:
                logger.info(f"No checkpoint found for thread: {new_thread_id}")
    except Exception as e:
        logger.warning(f"Could not access checkpointer: {e}")
    
    return updated_state