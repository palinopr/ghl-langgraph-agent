"""
Responder Agent - Fixed Version
Handles message deduplication more intelligently
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.utils.message_deduplication import is_duplicate_message, mark_message_sent
import asyncio

logger = get_logger("responder_agent")


async def responder_node_fixed(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed responder node that handles historical messages better.
    Only considers messages from the CURRENT workflow run as potential duplicates.
    """
    try:
        logger.info("Responder node (FIXED) processing...")
        
        # Get contact ID
        contact_id = state.get("contact_id")
        webhook_data = state.get("webhook_data", {})
        
        if not contact_id:
            contact_id = webhook_data.get("contactId", webhook_data.get("id"))
            
        if not contact_id:
            logger.error("No contact ID found in state or webhook data")
            return {
                "response_sent": False,
                "error": "Missing contact_id"
            }
        
        # Find the LAST agent message to send
        messages_to_send = []
        all_messages = state.get("messages", [])
        
        # Track which messages are from GHL history vs new
        historical_cutoff = None
        for i, msg in enumerate(all_messages):
            if isinstance(msg, AIMessage):
                # Check if this is a historical message
                additional_kwargs = getattr(msg, 'additional_kwargs', {})
                if additional_kwargs.get('source') == 'ghl_history':
                    historical_cutoff = i
        
        logger.info(f"Found {historical_cutoff + 1 if historical_cutoff else 0} historical messages")
        
        # Look for the last AI message from an agent (maria, carlos, or sofia)
        for i, msg in enumerate(reversed(all_messages[-10:])):
            msg_index = len(all_messages) - 1 - i  # Get actual index in all_messages
            
            if isinstance(msg, AIMessage) and msg.content:
                # Skip system messages from receptionist and supervisor
                msg_name = getattr(msg, 'name', '')
                if msg_name in ['receptionist', 'supervisor', 'supervisor_brain']:
                    continue
                
                # Check if this message is from GHL history
                additional_kwargs = getattr(msg, 'additional_kwargs', {})
                is_historical = additional_kwargs.get('source') == 'ghl_history'
                
                if is_historical:
                    logger.info(f"Skipping historical message: {msg.content[:50]}...")
                    continue
                
                # For new messages, check if it's EXACTLY the same as a recent historical message
                # This handles the case where agent generates identical response
                is_duplicate_of_history = False
                if historical_cutoff is not None:
                    # Check last few historical messages for exact match
                    for hist_msg in all_messages[max(0, historical_cutoff-5):historical_cutoff+1]:
                        if isinstance(hist_msg, AIMessage) and hist_msg.content == msg.content:
                            logger.info(f"New message matches historical message: {msg.content[:50]}...")
                            is_duplicate_of_history = True
                            break
                
                if is_duplicate_of_history:
                    # This is a new message but identical to history
                    # We should still send it because it's the agent's current response
                    logger.info("Message matches history but is new response - will send anyway")
                    messages_to_send.append(msg)
                    break
                
                # Check against deduplication system (for messages sent in this session)
                if not is_duplicate_message(contact_id, msg.content):
                    messages_to_send.append(msg)
                    break  # Only send ONE message
                else:
                    logger.info(f"Skipping duplicate from this session: {msg.content[:50]}...")
        
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
                    # Mark as sent in deduplication system
                    mark_message_sent(contact_id, msg.content)
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
        logger.error(f"Responder error: {str(e)}", exc_info=True)
        return {
            "response_sent": False,
            "responder_status": "error",
            "error": str(e)
        }