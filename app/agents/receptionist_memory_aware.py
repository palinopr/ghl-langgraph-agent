"""
Memory-Aware Receptionist Node
Enhanced with intelligent memory management
"""
import asyncio
from typing import Dict, Any, List
from app.utils.simple_logger import get_logger
from app.utils.memory_manager import get_memory_manager
from app.utils.context_filter import ContextFilter
from app.tools.conversation_loader import load_conversation_history_by_thread
from langchain_core.messages import HumanMessage, SystemMessage

logger = get_logger("receptionist_memory_aware")


async def receptionist_memory_aware_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced receptionist that properly manages memory and context
    
    Key improvements:
    1. Separates historical from current messages
    2. Initializes memory manager
    3. Loads only current thread
    4. Prevents context pollution
    """
    logger.info("=== MEMORY-AWARE RECEPTIONIST STARTING ===")
    
    # Get memory manager
    memory_manager = get_memory_manager()
    
    # Clear previous memories if new conversation
    if state.get("is_new_conversation", True):
        memory_manager.clear_all_memories()
        logger.info("Cleared all agent memories for new conversation")
    
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
    
    logger.info(f"Processing contact: {contact_id}")
    logger.info(f"Current message: {current_message}")
    
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
        
        # Load conversation history for CURRENT THREAD ONLY
        thread_messages = []
        if conversation_id:
            logger.info(f"Loading thread messages for conversation: {conversation_id}")
            thread_messages = await load_conversation_history_by_thread(
                contact_id=contact_id,
                location_id=location_id,
                conversation_id=conversation_id,
                limit=20  # Reasonable limit
            )
            logger.info(f"Loaded {len(thread_messages)} messages from current thread")
        
        # Separate current from historical using ContextFilter
        current_messages, historical_messages = ContextFilter.separate_current_from_historical(thread_messages)
        
        logger.info(f"Message separation: {len(current_messages)} current, {len(historical_messages)} historical")
        
        # Initialize messages list with current thread only
        messages = []
        
        # Add historical context as a summary (not full messages)
        if historical_messages:
            historical_summary = ContextFilter.extract_relevant_historical_context(
                historical_messages,
                current_topic="initial",
                extracted_data={}
            )
            if historical_summary:
                messages.append(SystemMessage(
                    content=historical_summary,
                    additional_kwargs={"type": "historical_summary"}
                ))
        
        # Add current thread messages
        messages.extend(current_messages)
        
        # Add the new incoming message
        new_message = HumanMessage(
            content=current_message,
            additional_kwargs={
                "contact_id": contact_id,
                "source": "webhook",
                "conversation_id": conversation_id
            }
        )
        messages.append(new_message)
        
        # Update state with clean data
        state.update({
            "messages": messages,  # Clean message list
            "contact_id": contact_id,
            "location_id": location_id,
            "conversation_id": conversation_id,
            "contact_info": contact_info,
            "previous_custom_fields": custom_fields,
            "is_new_conversation": len(current_messages) == 0,
            "thread_message_count": len(current_messages),
            "has_historical_context": len(historical_messages) > 0
        })
        
        # Initialize memory manager with current conversation
        for msg in current_messages[-6:]:  # Only recent messages
            if isinstance(msg, HumanMessage):
                memory_manager.add_agent_message("receptionist", msg)
        
        # Add current message to memory
        memory_manager.add_agent_message("receptionist", new_message)
        
        logger.info(f"Receptionist complete: {len(messages)} total messages in state")
        logger.info(f"Memory initialized with {len(current_messages)} messages")
        
    except Exception as e:
        logger.error(f"Error in memory-aware receptionist: {str(e)}", exc_info=True)
        
        # Fallback: Just add the current message
        state["messages"] = [HumanMessage(
            content=current_message,
            additional_kwargs={
                "contact_id": contact_id,
                "source": "webhook",
                "error": "failed_to_load_history"
            }
        )]
    
    return state