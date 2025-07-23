"""
Enhanced Thread ID Mapper Node
Attempts to override LangGraph Cloud's checkpoint configuration
Also handles message deduplication for LangGraph Cloud invocations
"""
from typing import Dict, Any, Optional
from app.utils.simple_logger import get_logger
from app.state.message_manager import MessageManager
from app.utils.debug_helpers import log_state_transition, validate_state
from app.utils.langsmith_debug import debug_node, log_to_langsmith, debug_state
import copy

logger = get_logger("thread_id_mapper")


@debug_node("thread_id_mapper")
async def thread_id_mapper_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced mapper that attempts to override checkpoint configuration
    to force LangGraph Cloud to use our consistent thread_ids.
    Also handles initial message deduplication for LangGraph Cloud.
    """
    logger.info("=== ENHANCED THREAD ID MAPPER STARTING ===")
    logger.info(f"State keys: {list(state.keys())}")
    
    # Log input state for debugging
    log_state_transition(state, "thread_mapper", "input")
    
    # Check for LangGraph Cloud pre-population issue
    messages = state.get("messages", [])
    webhook_body = state.get("webhook_data", {}).get("body", "")
    
    # Log webhook data to LangSmith
    if state.get("webhook_data"):
        log_to_langsmith({
            "webhook_contact_id": state["webhook_data"].get("contactId"),
            "webhook_conversation_id": state["webhook_data"].get("conversationId"),
            "webhook_body": webhook_body[:100] if webhook_body else None,
            "has_messages_prepopulated": len(messages) > 0,
        }, "webhook_analysis")
    
    if messages and webhook_body:
        # Check if the first message matches webhook body
        first_msg_content = ""
        if messages:
            first_msg = messages[0]
            if hasattr(first_msg, 'content'):
                first_msg_content = first_msg.content
            elif isinstance(first_msg, dict):
                first_msg_content = first_msg.get('content', '')
        
        if first_msg_content == webhook_body:
            logger.warning(f"⚠️ Detected LangGraph Cloud pre-population: message '{first_msg_content[:50]}...' appears in both messages and webhook_data")
            log_to_langsmith({
                "issue": "langgraph_cloud_prepopulation_detected",
                "first_message": first_msg_content[:100],
                "webhook_body": webhook_body[:100],
            }, "prepopulation_warning")
            # We'll let receptionist handle this by using MessageManager
    
    # Validate input state
    validation = validate_state(state, "thread_mapper_input")
    if not validation["valid"]:
        logger.warning(f"Input validation issues: {validation['issues']}")
    
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
    
    # NOTE: Removed checkpoint loading - only receptionist should load messages
    # This prevents message duplication in the state
    
    logger.info("=== ENHANCED THREAD ID MAPPER COMPLETE ===")
    
    # CRITICAL: Only return the fields we're updating, NOT the full state
    # Otherwise the state reducer will duplicate messages
    result = {
        "thread_id": new_thread_id,
        "mapped_thread_id": new_thread_id,
        "original_thread_id": original_thread_id,
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "__config__": updated_state.get("__config__")
    }
    
    # Log output for debugging
    log_state_transition(result, "thread_mapper", "output")
    
    return result


# Export
__all__ = ["thread_id_mapper_node"]