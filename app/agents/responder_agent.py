"""
Responder Agent - Dedicated agent for sending messages back to GHL
This agent runs after all other agents to ensure responses are sent
"""
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from app.state.conversation_state import ConversationState
from app.tools.ghl_client import GHLClient
from app.utils.simple_logger import get_logger
import asyncio

logger = get_logger("responder_agent")


async def responder_node(state: ConversationState) -> Dict[str, Any]:
    """
    Responder agent that sends all AI messages back to the customer via GHL.
    
    This agent:
    1. Collects all AI messages from the conversation
    2. Filters out messages already sent
    3. Sends new messages via GHL API
    4. Marks messages as sent to prevent duplicates
    
    Args:
        state: Current conversation state
        
    Returns:
        Updated state with response tracking
    """
    try:
        # Initialize GHL client
        ghl_client = GHLClient()
        
        # Get contact ID
        contact_id = state.get("contact_id")
        if not contact_id:
            logger.error("No contact_id found, cannot send messages")
            return {
                "response_sent": False,
                "error": "Missing contact_id"
            }
        
        # Find AI messages to send
        messages_to_send = []
        all_messages = state.get("messages", [])
        
        # Look through recent messages (last 10)
        for msg in all_messages[-10:]:
            if isinstance(msg, AIMessage) and msg.content:
                # Check if already sent (via metadata)
                metadata = getattr(msg, 'metadata', {})
                if not metadata.get('sent_to_ghl', False):
                    messages_to_send.append(msg)
        
        if not messages_to_send:
            logger.info("No new AI messages to send")
            return {
                "response_sent": True,
                "responder_status": "no_new_messages"
            }
        
        # Send messages
        logger.info(f"Sending {len(messages_to_send)} messages to contact {contact_id}")
        
        sent_count = 0
        failed_messages = []
        
        for i, msg in enumerate(messages_to_send):
            try:
                # Log what we're sending
                logger.info(f"Sending message {i+1}/{len(messages_to_send)}: {msg.content[:100]}...")
                
                # Send via GHL
                result = await ghl_client.send_message(
                    contact_id=contact_id,
                    message=msg.content,
                    message_type="WhatsApp"
                )
                
                if result:
                    sent_count += 1
                    # Mark as sent in metadata
                    if hasattr(msg, 'metadata'):
                        msg.metadata['sent_to_ghl'] = True
                    logger.info(f"✅ Message {i+1} sent successfully")
                else:
                    logger.error(f"❌ Failed to send message {i+1}")
                    failed_messages.append(msg.content[:50])
                
                # Natural delay between messages (0.5-1 second)
                if i < len(messages_to_send) - 1:
                    await asyncio.sleep(0.7)
                    
            except Exception as e:
                logger.error(f"Error sending message {i+1}: {str(e)}")
                failed_messages.append(f"Error: {str(e)[:50]}")
        
        # Summary
        success_rate = (sent_count / len(messages_to_send)) * 100 if messages_to_send else 0
        logger.info(f"Responder complete: {sent_count}/{len(messages_to_send)} messages sent ({success_rate:.0f}% success)")
        
        # Return state update
        return {
            "response_sent": sent_count > 0,
            "responder_status": "complete",
            "messages_sent_count": sent_count,
            "messages_failed_count": len(failed_messages),
            "failed_messages": failed_messages[:3] if failed_messages else []  # Keep first 3 for debugging
        }
        
    except Exception as e:
        logger.error(f"Critical error in responder_node: {str(e)}")
        return {
            "response_sent": False,
            "responder_status": "error",
            "error": str(e)
        }


# Alias for consistency with other agents
responder_agent = responder_node