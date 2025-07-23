#!/usr/bin/env python3
"""Check how the state reducer works"""

from typing import List, Annotated
from langchain_core.messages import HumanMessage, BaseMessage

# This is how our state is defined
messages: Annotated[List[BaseMessage], lambda x, y: x + y]

# Test the reducer
print("Testing state reducer behavior:")
print("=" * 50)

# Simulate what happens
existing = [HumanMessage(content="Hello")]
new_from_node = [HumanMessage(content="Hello")]

# The reducer does this:
result = existing + new_from_node
print(f"Existing: {len(existing)} messages")
print(f"Node returns: {len(new_from_node)} messages")
print(f"Result: {len(result)} messages")
print(f"Content: {[m.content for m in result]}")

print("\nThis explains the duplication!")
print("Each node that returns messages ADDS them to existing messages")
print("Instead of replacing them.")