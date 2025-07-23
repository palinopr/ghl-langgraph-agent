#!/usr/bin/env python3
"""
Debug the conversation analyzer
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import HumanMessage, AIMessage
from app.utils.conversation_analyzer import analyze_conversation_state

# Test with the exact message from the trace
messages = [
    HumanMessage(content="tengo un restaurante y estoy perdiendo clientes")
]

analysis = analyze_conversation_state(messages, agent_name="maria")

print(f"Stage: {analysis['stage']}")
print(f"Topics discussed: {analysis['topics_discussed']}")
print(f"Pending info: {analysis['pending_info']}")
print(f"\nAll content analyzed: '{' '.join(analysis['customer_messages'] + analysis['agent_messages'])}'")