"""
Simplified Receptionist - Only loads from GHL, no checkpoint messages
"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.utils.simple_logger import get_logger
from app.tools.ghl_client_simple import SimpleGHLClient
from app.tools.conversation_loader import ConversationLoader
from app.state.message_manager import MessageManager

logger = get_logger("receptionist")


async def receptionist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplified receptionist that ONLY loads messages from GHL
    No checkpoint loading, no duplication
    """
    logger.info("=== SIMPLE RECEPTIONIST STARTING ===")
    
    try:
        # Extract info from state
        contact_id = state.get("contact_id", "")
        conversation_id = state.get("conversation_id", "")
        webhook_data = state.get("webhook_data", {})
        current_message = webhook_data.get("body", "")
        
        logger.info(f"Processing contact: {contact_id}")
        logger.info(f"Conversation ID: {conversation_id}")
        logger.info(f"Current message: {current_message}")
        
        # Initialize GHL client
        ghl_client = SimpleGHLClient()
        loader = ConversationLoader(ghl_client)
        
        # Load conversation history from GHL ONLY
        messages = []
        if conversation_id:
            logger.info("Loading conversation history from GHL...")
            try:
                # Get ALL messages for this conversation
                ghl_messages = await loader.load_conversation_history(
                    contact_id=contact_id,
                    conversation_id=conversation_id,
                    limit=50  # Reasonable limit
                )
                
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
                logger.error(f"Failed to load GHL history: {e}")
        
        # Add current message
        messages.append(HumanMessage(
            content=current_message,
            additional_kwargs={
                "contact_id": contact_id,
                "source": "webhook"
            }
        ))
        
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
        
        # Return updated state with only new messages
        return {
            "messages": new_messages,  # Only new messages due to append reducer
            "contact_info": contact_info or {},
            "previous_custom_fields": custom_fields,
            "lead_score": lead_score,
            "last_message": current_message,
            "receptionist_complete": True,
            "is_first_contact": len(messages) <= 1,
            "thread_message_count": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Receptionist error: {str(e)}", exc_info=True)
        # Return minimal state on error
        return {
            "messages": [HumanMessage(content=webhook_data.get("body", "Error"))],
            "receptionist_complete": True,
            "last_message": webhook_data.get("body", ""),
            "is_first_contact": True
        }


# Export
__all__ = ["receptionist_node"]