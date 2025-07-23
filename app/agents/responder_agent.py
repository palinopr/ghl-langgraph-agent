"""
Responder - Robust message detection and sending
Production-ready responder agent
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage, BaseMessage
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.utils.langsmith_debug import debug_node, log_to_langsmith

logger = get_logger("responder")


def find_agent_response(messages: list[BaseMessage], current_agent: str) -> Optional[str]:
    """
    Find the most recent agent response to send
    
    Args:
        messages: List of all messages
        current_agent: The agent that just responded
        
    Returns:
        The message content to send, or None
    """
    # Strategy 1: If we know the current agent, find their last message
    if current_agent in ['maria', 'carlos', 'sofia']:
        logger.info(f"Looking for response from {current_agent}")
        
        # Look backwards for the most recent AI message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                # Check if it has the agent's name
                if hasattr(msg, 'name') and msg.name == current_agent:
                    logger.info(f"Found named message from {current_agent}")
                    return msg.content
                
                # If no name but it's the most recent AI message after knowing current agent
                # it's likely from that agent
                if not hasattr(msg, 'name') or not msg.name:
                    logger.info(f"Found unnamed AI message (assuming from {current_agent})")
                    return msg.content
    
    # Strategy 2: Find any recent AI message that looks like an agent response
    logger.info("Fallback: Looking for any agent-like response")
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content.strip()
            
            # Skip system messages (usually start with brackets or are very short)
            if content.startswith('[') or len(content) < 20:
                continue
                
            # Skip messages from supervisor
            if hasattr(msg, 'name') and msg.name == 'supervisor':
                continue
            
            # This looks like an agent response
            logger.info(f"Found agent-like message: {content[:50]}...")
            return content
    
    return None


@debug_node("responder")
async def responder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplified responder that's more robust
    """
    try:
        # Get contact info
        contact_id = state.get("contact_id")
        if not contact_id:
            logger.error("No contact_id in state")
            return {"message_sent": False, "error": "No contact_id"}
        
        # Get current agent
        current_agent = state.get("current_agent", "")
        logger.info(f"Current agent: {current_agent}")
        
        # Find the agent's response
        messages = state.get("messages", [])
        agent_response = find_agent_response(messages, current_agent)
        
        if not agent_response:
            logger.error("No agent response found to send")
            log_to_langsmith({
                "issue": "no_agent_response",
                "current_agent": current_agent,
                "message_count": len(messages),
                "last_3_messages": [
                    {
                        "type": type(m).__name__,
                        "has_content": bool(getattr(m, 'content', None)),
                        "name": getattr(m, 'name', 'no_name')
                    }
                    for m in messages[-3:] if messages
                ]
            }, "responder_error")
            return {"message_sent": False, "error": "No agent response found"}
        
        # Check if already sent
        if agent_response == state.get("last_sent_message"):
            logger.info("Message already sent, skipping")
            return {"message_sent": True, "duplicate": True}
        
        # Get message type
        webhook_data = state.get("webhook_data", {})
        message_type = webhook_data.get("type", "WhatsApp")
        
        # Send the message
        logger.info(f"Sending message: {agent_response[:50]}...")
        
        try:
            result = await ghl_client.send_message(
                contact_id,
                agent_response,
                message_type
            )
            
            if result:
                logger.info("✅ Message sent successfully")
                log_to_langsmith({
                    "action": "message_sent",
                    "contact_id": contact_id,
                    "agent": current_agent,
                    "message_length": len(agent_response),
                    "success": True
                }, "responder_success")
                
                return {
                    "message_sent": True,
                    "last_sent_message": agent_response,
                    "final_response": agent_response
                }
            else:
                logger.error("❌ GHL send_message returned None/False")
                return {
                    "message_sent": False,
                    "error": "GHL API returned no result"
                }
                
        except Exception as send_error:
            logger.error(f"Error sending message: {str(send_error)}", exc_info=True)
            return {
                "message_sent": False,
                "error": f"Send error: {str(send_error)}"
            }
            
    except Exception as e:
        logger.error(f"Responder error: {str(e)}", exc_info=True)
        return {
            "message_sent": False,
            "error": f"Responder error: {str(e)}"
        }