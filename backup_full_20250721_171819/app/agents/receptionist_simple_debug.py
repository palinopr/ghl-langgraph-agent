"""
Enhanced Debug Version of Receptionist Simple - With detailed logging
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from app.tools.ghl_client import GHLClient
from app.constants import FIELD_MAPPINGS
from app.utils.simple_logger import get_logger

logger = get_logger("receptionist_debug")


async def receptionist_simple_debug_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Debug version with extensive logging
    """
    contact_id = state.get("contact_id")
    logger.info(f"[DEBUG] Starting receptionist for contact {contact_id}")
    logger.info(f"[DEBUG] Initial state keys: {list(state.keys())}")
    logger.info(f"[DEBUG] Initial messages count: {len(state.get('messages', []))}")
    
    try:
        ghl_client = GHLClient()
        
        # 1. Load contact details
        logger.info("[DEBUG] Step 1: Loading contact details...")
        contact = await ghl_client.get_contact_details(contact_id)
        
        if not contact:
            logger.error(f"[DEBUG] Failed to load contact {contact_id}")
            return {
                "data_loaded": False,
                "error": "Contact not found"
            }
        
        logger.info(f"[DEBUG] Contact loaded: {contact.get('firstName')} {contact.get('lastName')}")
        
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
        
        logger.info(f"[DEBUG] Custom fields extracted: {custom_fields}")
        
        # 3. Load conversation history and convert to LangChain messages
        logger.info("[DEBUG] Step 3: Loading conversation history...")
        conversation_messages = []
        raw_messages = []
        
        try:
            logger.info(f"[DEBUG] Calling get_conversations for contact: {contact_id}")
            conversations = await ghl_client.get_conversations(contact_id)
            logger.info(f"[DEBUG] get_conversations returned: type={type(conversations)}, length={len(conversations) if conversations else 0}")
            
            if conversations and isinstance(conversations, list) and len(conversations) > 0:
                logger.info(f"[DEBUG] Found {len(conversations)} conversations")
                conv_id = conversations[0].get('id')
                logger.info(f"[DEBUG] Using conversation ID: {conv_id}")
                
                logger.info(f"[DEBUG] Calling get_conversation_messages...")
                conv_messages = await ghl_client.get_conversation_messages(conv_id)
                logger.info(f"[DEBUG] get_conversation_messages returned: type={type(conv_messages)}, length={len(conv_messages) if conv_messages else 0}")
                
                if conv_messages and isinstance(conv_messages, list):
                    raw_messages = conv_messages[-50:] if len(conv_messages) > 50 else conv_messages
                    logger.info(f"[DEBUG] Processing {len(raw_messages)} messages for conversion")
                    
                    # Convert GHL messages to LangChain format
                    for i, msg in enumerate(raw_messages):
                        content = msg.get('body', '') or msg.get('message', '')
                        direction = msg.get('direction', '').lower()
                        
                        logger.info(f"[DEBUG] Message {i+1}: direction={direction}, content_length={len(content)}, content_preview={content[:50]}")
                        
                        # Skip empty messages
                        if not content:
                            logger.info(f"[DEBUG] Skipping message {i+1}: empty content")
                            continue
                        
                        # Create appropriate message type
                        if direction == 'inbound' or msg.get('userId') == contact_id:
                            # Message from customer
                            logger.info(f"[DEBUG] Creating HumanMessage for message {i+1}")
                            conversation_messages.append(HumanMessage(
                                content=content,
                                additional_kwargs={
                                    "timestamp": msg.get('dateAdded', ''),
                                    "message_id": msg.get('id', ''),
                                    "source": "ghl_history"
                                }
                            ))
                        else:
                            # Message from agent/system
                            logger.info(f"[DEBUG] Creating AIMessage for message {i+1}")
                            conversation_messages.append(AIMessage(
                                content=content,
                                additional_kwargs={
                                    "timestamp": msg.get('dateAdded', ''),
                                    "message_id": msg.get('id', ''),
                                    "source": "ghl_history"
                                }
                            ))
                    
                    logger.info(f"[DEBUG] Conversion complete: {len(conversation_messages)} messages converted")
                else:
                    logger.warning("[DEBUG] conv_messages is not a list or is empty")
            else:
                logger.warning("[DEBUG] No conversations found or invalid format")
                
        except Exception as e:
            logger.error(f"[DEBUG] Exception in conversation loading: {type(e).__name__}: {str(e)}", exc_info=True)
        
        # 4. Create summary message
        logger.info("[DEBUG] Creating summary message...")
        summary = f"""
DATA LOADED SUCCESSFULLY:
- Contact: {contact.get('firstName', '')} {contact.get('lastName', '')}
- Email: {contact.get('email', 'none')}
- Phone: {contact.get('phone', '')}
- Previous Score: {custom_fields.get('score', '0')}/10
- Business: {custom_fields.get('business_type', 'not specified')}
- Budget: {custom_fields.get('budget', 'not confirmed')}
- Messages in history: {len(conversation_messages)}
"""
        
        # Add summary as AI message
        summary_msg = AIMessage(
            content=summary,
            name="receptionist"
        )
        
        # Combine all messages: history + current + summary
        logger.info(f"[DEBUG] Combining messages:")
        logger.info(f"[DEBUG] - History messages: {len(conversation_messages)}")
        logger.info(f"[DEBUG] - Current messages: {len(state.get('messages', []))}")
        logger.info(f"[DEBUG] - Summary message: 1")
        
        all_messages = conversation_messages + state.get("messages", []) + [summary_msg]
        logger.info(f"[DEBUG] Total messages after combination: {len(all_messages)}")
        
        # Return updated state with properly formatted messages
        result = {
            "messages": all_messages,  # Now includes full conversation history!
            "contact_info": contact,
            "previous_custom_fields": custom_fields,
            "conversation_history": raw_messages,  # Keep raw data for reference
            "formatted_history_count": len(conversation_messages),
            "data_loaded": True,
            "receptionist_complete": True
        }
        
        logger.info(f"[DEBUG] Returning state with:")
        logger.info(f"[DEBUG] - messages: {len(result['messages'])}")
        logger.info(f"[DEBUG] - conversation_history: {len(result['conversation_history'])}")
        logger.info(f"[DEBUG] - formatted_history_count: {result['formatted_history_count']}")
        
        return result
        
    except Exception as e:
        logger.error(f"[DEBUG] Receptionist error: {str(e)}", exc_info=True)
        error_msg = AIMessage(
            content=f"Failed to load data: {str(e)}",
            name="receptionist"
        )
        return {
            "messages": state.get("messages", []) + [error_msg],
            "data_loaded": False,
            "error": str(e)
        }