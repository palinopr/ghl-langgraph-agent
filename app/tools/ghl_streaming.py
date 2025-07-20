"""
Human-like Message Timing for GHL
Since GHL doesn't support real-time message editing, we simulate natural typing delays
"""
import asyncio
import time
from typing import Dict, Optional, List, Any
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger

logger = get_logger("ghl_streaming")


class HumanLikeResponder:
    """Adds natural delays before sending messages to feel more human"""
    
    def __init__(self):
        # Typing speed settings
        self.chars_per_second = 35     # Average human typing speed
        self.thinking_time = 0.8       # Base "thinking" time
        self.min_delay = 1.2           # Never respond faster than this
        self.max_delay = 4.5           # Never take longer than this
        
    def calculate_typing_delay(self, message: str) -> float:
        """
        Calculate realistic typing delay based on message length
        
        Args:
            message: The message to "type"
            
        Returns:
            Delay in seconds
        """
        # Base thinking time
        delay = self.thinking_time
        
        # Add typing time based on length
        typing_time = len(message) / self.chars_per_second
        delay += typing_time
        
        # Add extra time for complex messages
        if "?" in message:
            delay += 0.5  # Questions take longer to formulate
        if len(message.split()) > 20:
            delay += 0.7  # Long messages need more thought
        
        # Keep within bounds
        return max(self.min_delay, min(delay, self.max_delay))
    
    async def send_with_typing_delay(
        self,
        contact_id: str,
        message: str,
        message_type: str = "WhatsApp"
    ) -> Optional[Dict]:
        """
        Send message with natural typing delay
        
        Args:
            contact_id: GHL contact ID
            message: Message to send
            message_type: Type of message
            
        Returns:
            GHL response or None
        """
        # Calculate natural delay
        delay = self.calculate_typing_delay(message)
        
        logger.info(f"🤔 Thinking for {delay:.1f}s before responding...")
        
        # Show progress for longer delays
        if delay > 2.0:
            # Show typing indicator effect in logs
            steps = int(delay * 2)  # Update every 0.5s
            for i in range(steps):
                elapsed = (i + 1) * 0.5
                dots = "." * ((i % 3) + 1)
                logger.debug(f"Typing{dots} ({elapsed:.1f}s/{delay:.1f}s)")
                await asyncio.sleep(0.5)
            # Remaining time
            await asyncio.sleep(delay - (steps * 0.5))
        else:
            # Short delay, just wait
            await asyncio.sleep(delay)
        
        # Send the message
        logger.info(f"📤 Sending message after {delay:.1f}s delay")
        result = await ghl_client.send_message(
            contact_id,
            message,
            message_type
        )
        
        return result
    
    async def send_multi_part_message(
        self,
        contact_id: str,
        messages: List[str],
        message_type: str = "WhatsApp"
    ) -> List[Optional[Dict]]:
        """
        Send multiple messages with natural pauses between them
        
        Args:
            contact_id: GHL contact ID
            messages: List of messages to send
            message_type: Type of message
            
        Returns:
            List of GHL responses
        """
        results = []
        
        for i, message in enumerate(messages):
            # First message has normal delay
            if i == 0:
                result = await self.send_with_typing_delay(
                    contact_id, message, message_type
                )
            else:
                # Subsequent messages have shorter delays (like continuing a thought)
                delay = self.calculate_typing_delay(message) * 0.6
                logger.info(f"⏳ Brief pause ({delay:.1f}s) before next part...")
                await asyncio.sleep(delay)
                
                result = await ghl_client.send_message(
                    contact_id, message, message_type
                )
            
            results.append(result)
        
        return results


# Convenience function for easy integration
async def send_human_like_response(
    contact_id: str,
    message: str,
    message_type: str = "WhatsApp"
) -> Optional[Dict]:
    """
    Send a message with human-like typing delay
    
    Args:
        contact_id: GHL contact ID
        message: Message to send
        message_type: Type of message
        
    Returns:
        GHL response
    """
    responder = HumanLikeResponder()
    return await responder.send_with_typing_delay(contact_id, message, message_type)


# Demo function
async def demo_human_timing():
    """Demo different message timings"""
    responder = HumanLikeResponder()
    
    test_messages = [
        "¡Hola! 👋",
        "Claro, déjame revisar eso para ti.",
        "Perfecto, encontré la información que necesitas. Los horarios disponibles para esta semana son los siguientes:",
        "¿Te funciona alguno de estos horarios?"
    ]
    
    print("=" * 60)
    print("DEMO: Human-like Message Timing")
    print("=" * 60)
    
    for msg in test_messages:
        delay = responder.calculate_typing_delay(msg)
        print(f"\nMessage: {msg}")
        print(f"Length: {len(msg)} chars, {len(msg.split())} words")
        print(f"Delay: {delay:.1f} seconds")
        
        # Visual simulation
        print("Sending", end="", flush=True)
        for _ in range(int(delay * 2)):
            await asyncio.sleep(0.5)
            print(".", end="", flush=True)
        print(" ✓ Sent!")
    
    print("\n" + "=" * 60)
    print("Multi-part message example:")
    print("=" * 60)
    
    multi_messages = [
        "He revisado tu solicitud de cita...",
        "Tengo disponibilidad el martes a las 10am y el jueves a las 3pm.",
        "¿Cuál prefieres? 😊"
    ]
    
    start_time = time.time()
    for i, msg in enumerate(multi_messages):
        if i > 0:
            delay = responder.calculate_typing_delay(msg) * 0.6
            print(f"Pausing {delay:.1f}s...")
            await asyncio.sleep(delay)
        else:
            delay = responder.calculate_typing_delay(msg)
            print(f"Thinking {delay:.1f}s...")
            await asyncio.sleep(delay)
        print(f"→ {msg}")
    
    total_time = time.time() - start_time
    print(f"\nTotal time for 3-part message: {total_time:.1f} seconds")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo_human_timing())