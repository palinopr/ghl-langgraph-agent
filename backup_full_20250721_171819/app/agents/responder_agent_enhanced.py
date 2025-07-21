"""
Enhanced Responder Agent with detailed debugging
"""
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from app.state.conversation_state import ConversationState
from app.tools.ghl_client import GHLClient
from app.utils.simple_logger import get_logger
from app.utils.message_deduplication import is_duplicate_message, mark_message_sent
import asyncio

logger = get_logger("responder_enhanced")


async def responder_node_enhanced(state: ConversationState) -> Dict[str, Any]:
    """
    Enhanced responder with detailed debugging to find why messages aren't being sent
    """
    logger.info("=" * 60)
    logger.info("ENHANCED RESPONDER STARTING")
    logger.info("=" * 60)
    
    try:
        # Debug: Print state structure
        logger.info(f"State keys: {list(state.keys())}")
        
        # Get contact ID
        contact_id = state.get("contact_id")
        logger.info(f"Contact ID: {contact_id}")
        
        if not contact_id:
            logger.error("❌ No contact_id found")
            return {
                "response_sent": False,
                "responder_status": "no_contact_id",
                "error": "Missing contact_id"
            }
        
        # Get all messages
        all_messages = state.get("messages", [])
        logger.info(f"Total messages in state: {len(all_messages)}")
        
        # Debug: Show last 5 messages
        logger.info("\n📋 Last 5 messages in state:")
        for i, msg in enumerate(all_messages[-5:]):
            msg_type = type(msg).__name__
            msg_content = "No content"
            msg_name = "No name"
            
            if hasattr(msg, 'content'):
                msg_content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            
            if hasattr(msg, 'name'):
                msg_name = msg.name
                
            logger.info(f"  {i+1}. Type: {msg_type}, Name: {msg_name}, Content: {msg_content}")
        
        # Look for agent messages with more flexible matching
        agent_message = None
        agent_names = ['maria', 'carlos', 'sofia', 'maria_agent', 'carlos_agent', 'sofia_agent']
        
        logger.info("\n🔍 Searching for agent messages...")
        
        for msg in reversed(all_messages[-10:]):
            # Check different message types
            if isinstance(msg, (AIMessage, BaseMessage)):
                msg_name = getattr(msg, 'name', '').lower()
                msg_content = getattr(msg, 'content', '')
                
                logger.info(f"  Checking: name='{msg_name}', content='{msg_content[:30]}...'")
                
                # Skip system messages
                if msg_name in ['receptionist', 'supervisor', 'supervisor_brain', 'intelligence', 'responder']:
                    logger.info(f"    → Skipping system message from {msg_name}")
                    continue
                
                # Check if it's an agent message
                is_agent_msg = any(agent in msg_name for agent in agent_names) or not msg_name
                
                if is_agent_msg and msg_content:
                    # Skip debug messages
                    content_lower = msg_content.lower()
                    debug_patterns = [
                        'lead scored', 'routing to', 'data loaded',
                        'analysis complete', 'ghl updated', 'debug:',
                        'error:', 'loading', 'system:', 'info:'
                    ]
                    
                    if any(pattern in content_lower for pattern in debug_patterns):
                        logger.info(f"    → Skipping debug message")
                        continue
                    
                    # Found a valid agent message!
                    agent_message = msg
                    logger.info(f"    ✅ Found agent message!")
                    break
        
        if not agent_message:
            logger.warning("⚠️ No agent message found to send")
            
            # Additional debugging - check if there are any AI messages at all
            ai_messages = [msg for msg in all_messages if isinstance(msg, AIMessage)]
            logger.info(f"Total AI messages: {len(ai_messages)}")
            
            return {
                "response_sent": False,
                "responder_status": "no_agent_message",
                "debug_info": {
                    "total_messages": len(all_messages),
                    "ai_messages": len(ai_messages),
                    "last_message_type": type(all_messages[-1]).__name__ if all_messages else "None"
                }
            }
        
        # We have a message to send!
        message_content = agent_message.content
        logger.info(f"\n📤 Preparing to send message:")
        logger.info(f"  Content: {message_content}")
        logger.info(f"  Length: {len(message_content)} chars")
        
        # Check for duplicates
        if is_duplicate_message(contact_id, message_content):
            logger.info("⚠️ Message already sent (duplicate)")
            return {
                "response_sent": True,
                "responder_status": "duplicate_skipped"
            }
        
        # Initialize GHL client
        ghl_client = GHLClient()
        
        # Send the message
        logger.info("🚀 Sending message via GHL...")
        
        try:
            result = await ghl_client.send_message(
                contact_id=contact_id,
                message=message_content,
                message_type="WhatsApp"
            )
            
            logger.info(f"GHL Response: {result}")
            
            if result:
                # Mark as sent
                mark_message_sent(contact_id, message_content)
                logger.info("✅ Message sent successfully!")
                
                return {
                    "response_sent": True,
                    "responder_status": "sent",
                    "messages_sent_count": 1,
                    "sent_message": message_content[:100]
                }
            else:
                logger.error("❌ GHL returned False/None")
                return {
                    "response_sent": False,
                    "responder_status": "ghl_failed",
                    "error": "GHL send_message returned False"
                }
                
        except Exception as send_error:
            logger.error(f"❌ Error sending message: {send_error}")
            return {
                "response_sent": False,
                "responder_status": "send_error",
                "error": str(send_error)
            }
        
    except Exception as e:
        logger.error(f"❌ Critical error in responder: {str(e)}", exc_info=True)
        return {
            "response_sent": False,
            "responder_status": "critical_error",
            "error": str(e)
        }
    
    finally:
        logger.info("=" * 60)
        logger.info("RESPONDER COMPLETE")
        logger.info("=" * 60)