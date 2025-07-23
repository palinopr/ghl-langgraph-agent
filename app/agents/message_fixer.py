"""
Helper to ensure agent messages have proper names for routing
"""
from typing import List, Any
from langchain_core.messages import AIMessage, BaseMessage


def fix_agent_messages(messages: List[BaseMessage], agent_name: str) -> List[BaseMessage]:
    """
    Ensure AI messages from agents have the proper name attribute
    This helps the responder identify which messages to send
    """
    fixed_messages = []
    
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            # Create a new AIMessage with the agent name
            fixed_msg = AIMessage(
                content=msg.content,
                name=agent_name,
                additional_kwargs=msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {},
                tool_calls=msg.tool_calls if hasattr(msg, 'tool_calls') else []
            )
            fixed_messages.append(fixed_msg)
        else:
            # Keep other messages as-is
            fixed_messages.append(msg)
    
    return fixed_messages