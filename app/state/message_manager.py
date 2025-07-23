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
            # Normalize the content first
            content = ""
            if isinstance(msg, dict):
                content = msg.get('content', '')
            elif hasattr(msg, 'content'):
                content = msg.content
            else:
                content = str(msg)
            
            # Normalize the type/role
            msg_type = ""
            if isinstance(msg, dict):
                role = msg.get('role', msg.get('type', ''))
                # Normalize role names
                if role in ['human', 'user']:
                    msg_type = 'human'
                elif role in ['ai', 'assistant']:
                    msg_type = 'ai'
                else:
                    msg_type = role
            elif hasattr(msg, '__class__'):
                class_name = msg.__class__.__name__
                if class_name == 'HumanMessage':
                    msg_type = 'human'
                elif class_name == 'AIMessage':
                    msg_type = 'ai'
                else:
                    msg_type = class_name.lower()
            
            return (msg_type, content)
        
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
        # Use the same msg_key function for consistency
        def msg_key(msg):
            # Normalize the content first
            content = ""
            if isinstance(msg, dict):
                content = msg.get('content', '')
            elif hasattr(msg, 'content'):
                content = msg.content
            else:
                content = str(msg)
            
            # Normalize the type/role
            msg_type = ""
            if isinstance(msg, dict):
                role = msg.get('role', msg.get('type', ''))
                # Normalize role names
                if role in ['human', 'user']:
                    msg_type = 'human'
                elif role in ['ai', 'assistant']:
                    msg_type = 'ai'
                else:
                    msg_type = role
            elif hasattr(msg, '__class__'):
                class_name = msg.__class__.__name__
                if class_name == 'HumanMessage':
                    msg_type = 'human'
                elif class_name == 'AIMessage':
                    msg_type = 'ai'
                else:
                    msg_type = class_name.lower()
            
            return (msg_type, content)
        
        seen = set()
        deduplicated = []
        
        for msg in messages:
            key = msg_key(msg)
            if key not in seen:
                seen.add(key)
                deduplicated.append(msg)
        
        return deduplicated