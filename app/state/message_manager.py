"""
Message Manager - Handles message state updates to prevent duplication
"""
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


class MessageManager:
    """
    Manages message state updates to work with LangGraph's append-only message reducer
    """
    
    @staticmethod
    def set_messages(current_messages: List[BaseMessage], new_messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Replace current messages with new messages in a way that works with append reducer
        
        Since LangGraph uses `lambda x, y: x + y` for messages, we can't replace directly.
        Instead, we return only the NEW messages that aren't already in the state.
        """
        # Convert messages to comparable format
        def msg_key(msg):
            if isinstance(msg, dict):
                return (msg.get('role', ''), msg.get('content', ''))
            return (type(msg).__name__, msg.content)
        
        # Get existing message keys
        existing_keys = {msg_key(msg) for msg in current_messages}
        
        # Return only messages that aren't already present
        new_unique = []
        for msg in new_messages:
            if msg_key(msg) not in existing_keys:
                new_unique.append(msg)
        
        return new_unique
    
    @staticmethod
    def deduplicate_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Remove duplicate messages while preserving order
        """
        seen = set()
        deduplicated = []
        
        for msg in messages:
            # Create a key for comparison
            if isinstance(msg, dict):
                key = (msg.get('role', ''), msg.get('content', ''))
            else:
                key = (type(msg).__name__, msg.content)
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(msg)
        
        return deduplicated