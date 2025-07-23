"""
Simplified Receptionist - Only loads from GHL, no checkpoint messages
"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.utils.simple_logger import get_logger
from app.tools.ghl_client_simple import SimpleGHLClient
from app.state.message_manager import MessageManager
from app.utils.debug_helpers import log_state_transition, validate_state

logger = get_logger("receptionist")


async def receptionist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplified receptionist that ONLY loads messages from GHL
    No checkpoint loading, no duplication
    """
    logger.info("=== SIMPLE RECEPTIONIST STARTING ===")
    
    # Log input state for debugging
    log_state_transition(state, "receptionist", "input")
    
    try:
        # Extract info from state
        contact_id = state.get("contact_id", "")
        conversation_id = state.get("conversation_id", "")
        webhook_data = state.get("webhook_data", {})
        
        # Handle both webhook and direct invocation patterns
        if webhook_data and webhook_data.get("body"):
            # Webhook pattern: get message from webhook_data
            current_message = webhook_data.get("body", "")
            logger.info("Using webhook pattern for message")
        else:
            # Direct invocation: get last message from state
            state_messages = state.get("messages", [])
            if state_messages:
                last_msg = state_messages[-1]
                if isinstance(last_msg, dict):
                    current_message = last_msg.get("content", "")
                elif hasattr(last_msg, "content"):
                    current_message = last_msg.content
                else:
                    current_message = str(last_msg)
                logger.info("Using direct invocation pattern for message")
            else:
                current_message = ""
                logger.warning("No message found in webhook_data or state")
        
        logger.info(f"Processing contact: {contact_id}")
        logger.info(f"Conversation ID: {conversation_id}")
        logger.info(f"Current message: {current_message}")
        
        # Initialize GHL client
        ghl_client = SimpleGHLClient()
        
        # Load conversation history from GHL ONLY
        messages = []
        
        # Try to load conversation history
        logger.info(f"Attempting to load conversation history for contact: {contact_id}")
        
        # First, try with conversation_id if provided
        if conversation_id:
            logger.info(f"Using conversation_id: {conversation_id}")
            try:
                # Get messages directly from conversation
                ghl_messages = await ghl_client.get_conversation_messages(conversation_id)
                
                # Convert to LangChain messages
                for msg in ghl_messages:
                    if isinstance(msg, dict):
                        role = msg.get("role", "human")
                        content = msg.get("content", "")
                        if role == "user" or role == "human":
                            messages.append(HumanMessage(content=content))
                        else:
                            messages.append(AIMessage(content=content))
                    else:
                        messages.append(msg)
                
                logger.info(f"Loaded {len(messages)} messages from GHL")
                
            except Exception as e:
                logger.error(f"Failed to load messages by conversation_id: {e}")
                messages = []
        
        # If no conversation_id or failed, try loading by contact_id
        if not messages and contact_id:
            logger.info(f"Trying to load conversations by contact_id: {contact_id}")
            try:
                # Get all conversations for this contact
                conversations = await ghl_client.get_conversations(contact_id)
                logger.info(f"Found {len(conversations)} conversations for contact")
                
                if conversations:
                    # Get the most recent conversation
                    recent_conv = conversations[0]  # They're usually sorted by recency
                    conv_id = recent_conv.get('id')
                    logger.info(f"Loading messages from most recent conversation: {conv_id}")
                    
                    # Get messages from this conversation
                    ghl_messages = await ghl_client.get_conversation_messages(conv_id)
                    
                    # Convert to LangChain messages
                    for msg in ghl_messages:
                        if isinstance(msg, dict):
                            role = msg.get("role", "human")
                            content = msg.get("content", "") or msg.get("body", "")
                            if role == "user" or role == "human":
                                messages.append(HumanMessage(content=content))
                            else:
                                messages.append(AIMessage(content=content))
                        else:
                            messages.append(msg)
                    
                    logger.info(f"Loaded {len(messages)} messages from conversation")
                else:
                    logger.warning("No conversations found for this contact")
                    
            except Exception as e:
                logger.error(f"Failed to load by contact_id: {e}", exc_info=True)
        
        # Add current message ONLY if it's not already in the loaded messages
        # This prevents duplication when message is already in state
        should_add_current = True
        
        # Check if current message is already in the loaded messages
        for msg in messages:
            msg_content = ""
            if isinstance(msg, dict):
                msg_content = msg.get("content", "")
            elif hasattr(msg, "content"):
                msg_content = msg.content
            
            if msg_content == current_message:
                should_add_current = False
                logger.info("Current message already in history, not adding again")
                break
        
        if should_add_current and current_message:
            messages.append(HumanMessage(
                content=current_message,
                additional_kwargs={
                    "contact_id": contact_id,
                    "source": "webhook"
                }
            ))
            logger.info("Added current message to history")
        
        # Get contact info
        contact_info = None
        custom_fields = {}
        try:
            if contact_id:
                contact_info = await ghl_client.get_contact(contact_id)
                custom_fields = contact_info.get("customFields", {}) if contact_info else {}
        except Exception as e:
            logger.error(f"Failed to get contact info: {e}")
        
        # Extract lead score if available
        lead_score = 0
        if custom_fields:
            lead_score_str = custom_fields.get("wAPjuqxtfgKLCJqahjo1", "0")
            try:
                lead_score = int(lead_score_str) if lead_score_str else 0
            except:
                lead_score = 0
        
        logger.info(f"Total messages: {len(messages)}, Lead score: {lead_score}")
        
        # Get current messages in state to avoid duplication
        current_state_messages = state.get("messages", [])
        
        # Use MessageManager to only return new messages
        new_messages = MessageManager.set_messages(current_state_messages, messages)
        
        logger.info(f"Current state has {len(current_state_messages)} messages")
        logger.info(f"Returning {len(new_messages)} new messages to avoid duplication")
        
        # Prepare result
        result = {
            "messages": new_messages,  # Only new messages due to append reducer
            "contact_info": contact_info or {},
            "previous_custom_fields": custom_fields,
            "lead_score": lead_score,
            "last_message": current_message,
            "receptionist_complete": True,
            "is_first_contact": len(messages) <= 1,
            "thread_message_count": len(messages)
        }
        
        # Log output state for debugging
        log_state_transition(result, "receptionist", "output")
        
        # Validate output state
        validation = validate_state(result, "receptionist")
        if not validation["valid"]:
            logger.warning(f"Output validation issues: {validation['issues']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Receptionist error: {str(e)}", exc_info=True)
        
        # Even on error, use MessageManager to avoid duplication
        current_state_messages = state.get("messages", [])
        
        # Get the original message content from state
        webhook_data = state.get("webhook_data", {})
        original_content = webhook_data.get("body", "")
        if not original_content and current_state_messages:
            # Try to get from last message
            last_msg = current_state_messages[-1]
            if isinstance(last_msg, dict):
                original_content = last_msg.get("content", "")
            elif hasattr(last_msg, "content"):
                original_content = last_msg.content
        
        # Create error message with original content if available
        error_message = HumanMessage(content=original_content if original_content else "Error processing message")
        
        # Only add the error message if it's not already in state
        new_messages = MessageManager.set_messages(current_state_messages, [error_message])
        
        # Return minimal state on error
        return {
            "messages": new_messages,  # Use MessageManager even for errors
            "receptionist_complete": True,
            "last_message": error_message.content,
            "is_first_contact": True
        }


# Export
__all__ = ["receptionist_node"]