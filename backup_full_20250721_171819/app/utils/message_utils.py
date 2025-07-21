"""
Message utilities for managing conversation history
Implements message trimming to prevent token overflow
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, trim_messages, HumanMessage, AIMessage
from app.utils.simple_logger import get_logger

logger = get_logger("message_utils")


def trim_message_history(
    messages: List[BaseMessage],
    max_tokens: int = 10000,
    strategy: str = "last",
    include_system: bool = True,
    start_on: str = "human"
) -> List[BaseMessage]:
    """
    Trim message history to fit within token limits
    
    Args:
        messages: List of messages to trim
        max_tokens: Maximum token count (default 10k for GPT-4)
        strategy: Trimming strategy ("last" keeps recent messages)
        include_system: Whether to keep system messages
        start_on: Start conversation on "human" or "ai"
        
    Returns:
        Trimmed list of messages
    """
    if not messages:
        return messages
    
    try:
        # Use LangChain's trim_messages utility
        trimmed = trim_messages(
            messages,
            max_tokens=max_tokens,
            strategy=strategy,
            token_counter=len,  # Simple token counter, can be improved
            include_system=include_system,
            start_on=start_on
        )
        
        if len(trimmed) < len(messages):
            logger.info(
                f"Trimmed messages from {len(messages)} to {len(trimmed)} "
                f"(max_tokens={max_tokens})"
            )
        
        return trimmed
        
    except Exception as e:
        logger.error(f"Error trimming messages: {e}")
        # Fallback: keep last N messages
        return messages[-20:] if len(messages) > 20 else messages


def create_conversation_summary(
    messages: List[BaseMessage],
    max_length: int = 500
) -> str:
    """
    Create a summary of the conversation for context
    
    Args:
        messages: List of messages
        max_length: Maximum summary length
        
    Returns:
        Summary string
    """
    if not messages:
        return "No conversation history."
    
    summary_parts = []
    
    # Count message types
    human_count = sum(1 for m in messages if isinstance(m, HumanMessage))
    ai_count = sum(1 for m in messages if isinstance(m, AIMessage))
    
    summary_parts.append(f"Conversation: {human_count} user messages, {ai_count} assistant messages")
    
    # Get key topics discussed (simple keyword extraction)
    all_text = " ".join(m.content for m in messages if hasattr(m, 'content'))
    
    # Look for business mentions
    if "restaurante" in all_text.lower():
        summary_parts.append("Business: Restaurant")
    elif "tienda" in all_text.lower():
        summary_parts.append("Business: Store")
    
    # Look for budget mentions
    if "$" in all_text or "presupuesto" in all_text.lower():
        summary_parts.append("Budget: Discussed")
    
    # Look for appointment mentions
    if "cita" in all_text.lower() or "appointment" in all_text.lower():
        summary_parts.append("Appointment: Requested")
    
    summary = " | ".join(summary_parts)
    
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."
    
    return summary


def prepare_messages_for_model(
    messages: List[BaseMessage],
    model_name: str = "gpt-4",
    add_summary: bool = True
) -> List[BaseMessage]:
    """
    Prepare messages for model consumption with proper trimming
    
    Args:
        messages: Raw message list
        model_name: Model being used
        add_summary: Whether to add conversation summary
        
    Returns:
        Prepared message list
    """
    # Token limits by model
    token_limits = {
        "gpt-4": 8000,
        "gpt-4-turbo": 16000,
        "gpt-3.5-turbo": 4000,
        "claude-3": 100000
    }
    
    max_tokens = token_limits.get(model_name, 8000)
    
    # Trim messages if needed
    trimmed = trim_message_history(messages, max_tokens=max_tokens)
    
    # If messages were trimmed and add_summary is True, prepend summary
    if add_summary and len(trimmed) < len(messages):
        summary = create_conversation_summary(messages[:len(messages)-len(trimmed)])
        summary_message = AIMessage(
            content=f"[Previous conversation summary: {summary}]"
        )
        trimmed = [summary_message] + trimmed
    
    return trimmed


# Pre-built configurations for different scenarios
MESSAGE_TRIM_CONFIGS = {
    "standard": {
        "max_tokens": 8000,
        "strategy": "last",
        "include_system": True,
        "start_on": "human"
    },
    "extended": {
        "max_tokens": 16000,
        "strategy": "last",
        "include_system": True,
        "start_on": "human"
    },
    "minimal": {
        "max_tokens": 4000,
        "strategy": "last",
        "include_system": False,
        "start_on": "human"
    }
}


def get_trimmed_messages(
    messages: List[BaseMessage],
    config_name: str = "standard"
) -> List[BaseMessage]:
    """
    Get trimmed messages using a pre-built configuration
    
    Args:
        messages: Messages to trim
        config_name: Configuration name (standard, extended, minimal)
        
    Returns:
        Trimmed messages
    """
    config = MESSAGE_TRIM_CONFIGS.get(config_name, MESSAGE_TRIM_CONFIGS["standard"])
    return trim_message_history(messages, **config)


__all__ = [
    "trim_message_history",
    "create_conversation_summary",
    "prepare_messages_for_model",
    "get_trimmed_messages",
    "MESSAGE_TRIM_CONFIGS"
]