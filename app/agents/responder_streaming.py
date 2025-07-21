"""
Enhanced Responder with Human-like Timing
Sends messages with natural typing delays
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from app.tools.ghl_streaming import send_human_like_response, HumanLikeResponder
from app.utils.simple_logger import get_logger

logger = get_logger("responder_streaming")


async def responder_streaming_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced responder with human-like typing delays
    """
    try:
        # Get contact info
        contact_id = state.get("contact_id")
        if not contact_id:
            logger.error("No contact_id in state")
            return state
        
        # Get the last message from the conversation
        messages = state.get("messages", [])
        if not messages:
            logger.warning("No messages to respond to")
            return state
        
        # Find the last AI message to send (from actual agents only)
        last_ai_message = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                # Only send messages from actual agents, not system messages
                msg_name = getattr(msg, 'name', '')
                if msg_name in ['maria', 'carlos', 'sofia']:
                    last_ai_message = msg
                    break
                # Also check for agent messages without explicit name
                elif not msg_name and msg.content and not msg.content.startswith('['):
                    # Likely an agent message if it has content and doesn't start with system brackets
                    last_ai_message = msg
                    break
        
        if not last_ai_message:
            logger.warning("No AI message found to send")
            return state
        
        # Check if we already sent this message
        if last_ai_message.content == state.get("last_sent_message"):
            logger.info("Message already sent, skipping")
            return state
        
        # Get message type from webhook data
        webhook_data = state.get("webhook_data", {})
        message_type = webhook_data.get("type", "WhatsApp")
        
        logger.info(f"💬 Preparing to send: {last_ai_message.content[:50]}...")
        
        # Split message if it contains multiple parts (separated by double newlines)
        message_parts = last_ai_message.content.split('\n\n')
        
        if len(message_parts) > 1 and all(len(part.strip()) > 0 for part in message_parts):
            # Multi-part message - send with natural pauses
            logger.info(f"📝 Sending {len(message_parts)}-part message with natural pauses")
            
            responder = HumanLikeResponder()
            results = await responder.send_multi_part_message(
                contact_id,
                message_parts,
                message_type
            )
            
            logger.info(f"✓ Sent all {len(message_parts)} parts with human-like timing")
        else:
            # Single message - send with typing delay
            logger.info("📤 Sending single message with typing delay")
            
            result = await send_human_like_response(
                contact_id,
                last_ai_message.content,
                message_type
            )
            
            logger.info(f"✓ Message sent after natural delay")
        
        # Update state to track sent message
        return {
            "last_sent_message": last_ai_message.content,
            "message_sent": True
        }
        
    except Exception as e:
        logger.error(f"Error in streaming responder: {str(e)}", exc_info=True)
        # Fallback to regular sending
        try:
            from app.tools.ghl_client import ghl_client
            await ghl_client.send_message(
                contact_id,
                last_ai_message.content if 'last_ai_message' in locals() else "Lo siento, ocurrió un error.",
                message_type
            )
        except:
            pass
        return state


# Demo function to show streaming effect
async def demo_streaming_responder():
    """Demo the streaming responder"""
    import asyncio
    from datetime import datetime
    
    # Create mock state
    mock_state = {
        "contact_id": "demo123",
        "webhook_data": {"type": "WhatsApp"},
        "messages": [
            HumanMessage(content="Hola, necesito agendar una cita"),
            AIMessage(content="""¡Perfecto! Me encantaría ayudarte a agendar tu consulta gratuita sobre automatización de WhatsApp.

Tengo estos horarios disponibles para esta semana:
📅 Martes 23 a las 10:00 AM
📅 Miércoles 24 a las 2:00 PM
📅 Jueves 25 a las 4:00 PM

¿Cuál de estos horarios te funciona mejor? 😊""")
        ]
    }
    
    print("=" * 50)
    print("DEMO: Token Streaming Responder")
    print("=" * 50)
    print(f"Contact: {mock_state['contact_id']}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("\nStreaming response with typing effect...")
    print("-" * 50)
    
    # Simulate the streaming visually
    message = mock_state["messages"][-1].content
    for char in message:
        print(char, end="", flush=True)
        if char == ' ':
            await asyncio.sleep(0.1)  # Word delay
        elif char in '.!?':
            await asyncio.sleep(0.3)  # Sentence delay
        else:
            await asyncio.sleep(0.03)  # Character delay
    
    print("\n" + "-" * 50)
    print("✓ Message streamed successfully!")
    print(f"Total characters: {len(message)}")
    print(f"Estimated time: ~{len(message.split()) * 0.15:.1f} seconds")


if __name__ == "__main__":
    # Run the demo
    import asyncio
    asyncio.run(demo_streaming_responder())