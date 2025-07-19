"""
Simplified Receptionist Agent - Just loads data
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage, ToolMessage
from app.tools.ghl_client import GHLClient
from app.constants import FIELD_MAPPINGS
from app.utils.simple_logger import get_logger

logger = get_logger("receptionist_simple")


async def receptionist_simple_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple receptionist that directly loads data without agent complexity
    """
    contact_id = state.get("contact_id")
    logger.info(f"Receptionist loading data for contact {contact_id}")
    
    try:
        ghl_client = GHLClient()
        
        # 1. Load contact details
        logger.info("Loading contact details...")
        contact = await ghl_client.get_contact_details(contact_id)
        
        if not contact:
            logger.error(f"Failed to load contact {contact_id}")
            return {
                "data_loaded": False,
                "error": "Contact not found"
            }
        
        # 2. Extract custom fields
        custom_fields = {}
        for field in contact.get('customFields', []):
            field_id = field.get('id')
            field_value = field.get('value', '')
            
            # Map to readable names
            for name, mapped_id in FIELD_MAPPINGS.items():
                if mapped_id == field_id:
                    custom_fields[name] = field_value
                    break
        
        logger.info(f"Loaded custom fields: {custom_fields}")
        
        # 3. Load conversation history
        logger.info("Loading conversation history...")
        messages = []
        try:
            conversations = await ghl_client.get_conversations(contact_id)
            if conversations and isinstance(conversations, list) and len(conversations) > 0:
                conv_id = conversations[0].get('id')
                conv_messages = await ghl_client.get_conversation_messages(conv_id)
                if conv_messages and isinstance(conv_messages, list):
                    messages = conv_messages[-50:] if len(conv_messages) > 50 else conv_messages
                    logger.info(f"Loaded {len(messages)} historical messages")
        except Exception as e:
            logger.warning(f"Could not load conversation history: {e}")
        
        # 4. Create summary message
        summary = f"""
DATA LOADED SUCCESSFULLY:
- Contact: {contact.get('firstName', '')} {contact.get('lastName', '')}
- Email: {contact.get('email', 'none')}
- Phone: {contact.get('phone', '')}
- Previous Score: {custom_fields.get('score', '0')}/10
- Business: {custom_fields.get('business_type', 'not specified')}
- Budget: {custom_fields.get('budget', 'not confirmed')}
- Messages in history: {len(messages)}
"""
        
        # Add summary as AI message
        summary_msg = AIMessage(
            content=summary,
            name="receptionist"
        )
        
        # Return updated state
        return {
            "messages": state.get("messages", []) + [summary_msg],
            "contact_info": contact,
            "previous_custom_fields": custom_fields,
            "conversation_history": messages,
            "data_loaded": True,
            "receptionist_complete": True
        }
        
    except Exception as e:
        logger.error(f"Receptionist error: {str(e)}", exc_info=True)
        error_msg = AIMessage(
            content=f"Failed to load data: {str(e)}",
            name="receptionist"
        )
        return {
            "messages": state.get("messages", []) + [error_msg],
            "data_loaded": False,
            "error": str(e)
        }