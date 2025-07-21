"""
Typing Simulator - Adds realistic typing indicators for human-like conversations
Integrates with GHL to show typing status
"""
import asyncio
import random
from typing import Optional, Dict, Any
from app.utils.simple_logger import get_logger
from app.tools.ghl_client import ghl_client

logger = get_logger("typing_simulator")


class TypingSimulator:
    """
    Simulates human typing patterns with GHL integration
    Shows typing indicators before sending messages
    """
    
    @staticmethod
    async def simulate_typing(
        contact_id: str,
        message_length: int,
        agent_name: str = "maria",
        is_thinking: bool = False
    ) -> float:
        """
        Simulate typing and return duration
        
        Args:
            contact_id: GHL contact ID
            message_length: Length of message being typed
            agent_name: Agent typing (affects speed)
            is_thinking: Whether agent is thinking (adds pause)
        
        Returns:
            Total duration of typing simulation
        """
        try:
            # Calculate base typing duration
            # Average human typing: 40 WPM = ~200 chars/min = ~3.3 chars/sec
            base_speed = {
                "maria": 3.0,    # Warm, deliberate
                "carlos": 3.5,   # Professional, faster
                "sofia": 4.0     # Efficient, fastest
            }.get(agent_name, 3.3)
            
            # Add variability (±20%)
            speed = base_speed * random.uniform(0.8, 1.2)
            
            # Calculate typing time
            typing_duration = message_length / speed
            
            # Add thinking time if needed
            thinking_duration = 0
            if is_thinking:
                thinking_duration = random.uniform(1.0, 2.5)
            
            # Cap total duration
            total_duration = min(typing_duration + thinking_duration, 5.0)
            
            # Send typing indicator to GHL
            await TypingSimulator._send_typing_indicator(contact_id, True)
            
            # Wait for typing duration
            await asyncio.sleep(total_duration)
            
            # Stop typing indicator
            await TypingSimulator._send_typing_indicator(contact_id, False)
            
            return total_duration
            
        except Exception as e:
            logger.error(f"Error simulating typing: {e}")
            return 0.5  # Fallback duration
    
    @staticmethod
    async def _send_typing_indicator(contact_id: str, is_typing: bool) -> None:
        """Send typing indicator to GHL"""
        try:
            # GHL doesn't have a direct typing API, but we can use custom events
            # or integrate with their websocket if available
            # For now, we'll just log it
            logger.info(f"{'Starting' if is_typing else 'Stopping'} typing for {contact_id}")
            
            # If GHL adds typing API in future:
            # await ghl_client.send_typing_status(contact_id, is_typing)
            
        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
    
    @staticmethod
    def should_show_typing(
        message: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if typing indicator should be shown
        
        Args:
            message: Message to be sent
            context: Conversation context
        
        Returns:
            Whether to show typing indicator
        """
        # Always show for longer messages
        if len(message) > 50:
            return True
        
        # Show when switching topics/agents
        if context.get("agent_switch", False):
            return True
        
        # Show for questions
        if "?" in message:
            return True
        
        # Random chance for shorter messages (30%)
        return random.random() < 0.3
    
    @staticmethod
    def calculate_pause_between_messages(
        previous_message: str,
        current_message: str,
        agent_name: str
    ) -> float:
        """
        Calculate natural pause between messages
        
        Args:
            previous_message: Previous message sent
            current_message: Current message to send
            agent_name: Agent sending message
        
        Returns:
            Pause duration in seconds
        """
        base_pause = 0.5
        
        # Longer pause if switching topics
        if "?" in previous_message and "?" not in current_message:
            base_pause += random.uniform(0.5, 1.0)
        
        # Personality-based pauses
        personality_pause = {
            "maria": 0.3,    # Thoughtful
            "carlos": 0.2,   # Engaged
            "sofia": 0.1     # Quick
        }.get(agent_name, 0.2)
        
        # Add randomness
        total_pause = base_pause + personality_pause + random.uniform(0, 0.5)
        
        return min(total_pause, 2.0)  # Cap at 2 seconds
    
    @staticmethod
    async def send_with_typing(
        contact_id: str,
        message: str,
        agent_name: str = "maria",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send message with typing simulation
        
        Args:
            contact_id: GHL contact ID
            message: Message to send
            agent_name: Agent sending message
            context: Optional conversation context
        """
        context = context or {}
        
        # Determine if we should show typing
        if TypingSimulator.should_show_typing(message, context):
            # Check if agent is thinking
            is_thinking = any(phrase in message for phrase in [
                "Déjame ver", "A ver", "Let me see", "Hmm"
            ])
            
            # Simulate typing
            await TypingSimulator.simulate_typing(
                contact_id=contact_id,
                message_length=len(message),
                agent_name=agent_name,
                is_thinking=is_thinking
            )
        
        # Message will be sent by the responder
        logger.info(f"Completed typing simulation for {agent_name}")
    
    @staticmethod
    def split_long_message(message: str, max_length: int = 300) -> list[str]:
        """
        Split long messages into natural chunks
        Simulates how humans send multiple shorter messages
        
        Args:
            message: Long message to split
            max_length: Maximum length per chunk
        
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        sentences = message.split(". ")
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If we couldn't split by sentences, force split
        if len(chunks) == 1 and len(chunks[0]) > max_length:
            text = chunks[0]
            chunks = []
            while text:
                # Try to split at a space
                if len(text) > max_length:
                    split_point = text[:max_length].rfind(" ")
                    if split_point == -1:
                        split_point = max_length
                    chunks.append(text[:split_point])
                    text = text[split_point:].strip()
                else:
                    chunks.append(text)
                    break
        
        return chunks