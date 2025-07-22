"""
Message utility functions
"""
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage

def get_trimmed_messages(messages: List[BaseMessage], config_name: str = "default") -> List[BaseMessage]:
    """
    Trim messages to fit within token limits
    
    For now, just return the last 50 messages
    """
    return messages[-50:]