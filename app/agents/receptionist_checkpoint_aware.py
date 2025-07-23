"""
Checkpoint-Aware Receptionist Node
Properly loads conversation history from LangGraph checkpointer
"""
import asyncio
from typing import Dict, Any, List, Optional
from app.utils.simple_logger import get_logger
from app.tools.conversation_loader import ConversationLoader
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.checkpoint.base import BaseCheckpointSaver

logger = get_logger("receptionist_checkpoint_aware")


async def receptionist_checkpoint_aware_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced receptionist that loads conversation history from checkpointer
    
    Key improvements:
    1. Loads from LangGraph checkpointer for true state persistence
    2. Uses consistent thread_id for conversation continuity
    3. Merges checkpoint history with current message
    4. Prevents context loss and repetitive questions
    """
    logger.info("=== CHECKPOINT-AWARE RECEPTIONIST STARTING ===")
    
    # Extract webhook data
    webhook_data = state.get("webhook_data", {})
    contact_id = webhook_data.get("contactId")
    location_id = webhook_data.get("locationId", "sHFG9Rw6BdGh6d6bfMqG")
    conversation_id = webhook_data.get("conversationId")
    
    # Get current message
    current_message = webhook_data.get("body", "")
    
    if not contact_id:
        logger.error("No contact ID provided")
        return state
    
    # CRITICAL FIX: Use consistent thread_id
    thread_id = state.get("thread_id") or f"contact-{contact_id}"
    logger.info(f"Using thread_id: {thread_id} for checkpoint loading")
    
    logger.info(f"Processing contact: {contact_id}")
    logger.info(f"Current message: {current_message}")
    logger.info(f"Conversation ID: {conversation_id}")
    
    try:
        # Load GHL data in parallel
        from app.tools.ghl_client import ghl_client
        
        # Parallel load for speed
        contact_info, custom_fields = await asyncio.gather(
            ghl_client.get_contact(contact_id),
            ghl_client.get_contact_custom_fields(contact_id),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(contact_info, Exception):
            logger.error(f"Failed to load contact: {contact_info}")
            contact_info = {}
        
        if isinstance(custom_fields, Exception):
            logger.error(f"Failed to load custom fields: {custom_fields}")
            custom_fields = {}
        
        # Get existing messages from state (from checkpointer)
        existing_messages = state.get("messages", [])
        logger.info(f"Found {len(existing_messages)} existing messages in checkpoint")
        
        # Also try to load from GHL for current thread
        thread_messages = []
        if conversation_id and len(existing_messages) == 0:
            logger.info(f"No checkpoint messages, loading from GHL for conversation: {conversation_id}")
            loader = ConversationLoader()
            thread_messages = await loader.load_conversation_history(
                contact_id=contact_id,
                thread_id=conversation_id,
                limit=20
            )
            logger.info(f"Loaded {len(thread_messages)} messages from GHL")
        
        # Merge messages: checkpoint takes precedence
        if existing_messages:
            # Use checkpoint messages
            messages = list(existing_messages)
            logger.info(f"Using {len(messages)} messages from checkpoint")
        else:
            # Use GHL messages if no checkpoint
            messages = thread_messages
            logger.info(f"Using {len(messages)} messages from GHL (no checkpoint)")
        
        # Debug: Show last few messages for context
        if messages:
            logger.info("=== CONVERSATION CONTEXT ===")
            for i, msg in enumerate(messages[-3:]):  # Last 3 messages
                # Handle both dict and object messages
                if isinstance(msg, dict):
                    msg_content = str(msg.get('content', ''))[:100]
                    msg_type = msg.get('type', 'unknown')
                else:
                    msg_content = str(getattr(msg, 'content', ''))[:100]
                    msg_type = type(msg).__name__
                logger.info(f"  [{i-3}] {msg_type}: {msg_content}...")
            logger.info("=== END CONTEXT ===")
        
        # Add the new incoming message
        new_message = HumanMessage(
            content=current_message,
            additional_kwargs={
                "contact_id": contact_id,
                "source": "webhook",
                "conversation_id": conversation_id,
                "timestamp": webhook_data.get("timestamp", "")
            }
        )
        messages.append(new_message)
        
        # Determine if this is a new conversation
        is_new_conversation = len(messages) <= 1  # Only the new message
        
        # Update state with complete data
        state.update({
            "messages": messages,  # Full conversation history
            "contact_id": contact_id,
            "location_id": location_id,
            "conversation_id": conversation_id,
            "thread_id": thread_id,  # Ensure consistent thread_id
            "contact_info": contact_info,
            "previous_custom_fields": custom_fields,
            "is_new_conversation": is_new_conversation,
            "thread_message_count": len(messages) - 1,  # Exclude new message
            "has_checkpoint": len(existing_messages) > 0
        })
        
        logger.info(f"Receptionist complete: {len(messages)} total messages")
        logger.info(f"Conversation type: {'NEW' if is_new_conversation else 'ONGOING'}")
        logger.info(f"Checkpoint status: {'LOADED' if len(existing_messages) > 0 else 'EMPTY'}")
        
    except Exception as e:
        logger.error(f"Error in checkpoint-aware receptionist: {str(e)}", exc_info=True)
        
        # Fallback: Just add the current message
        state["messages"] = [HumanMessage(
            content=current_message,
            additional_kwargs={
                "contact_id": contact_id,
                "source": "webhook",
                "error": "failed_to_load_history"
            }
        )]
        state["thread_id"] = thread_id
    
    return state