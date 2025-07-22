#!/usr/bin/env python3
"""
Check if async functions are being executed properly
"""

import asyncio
import inspect
from app.agents.responder_streaming import responder_streaming_node

# Check if the function is async
print(f"responder_streaming_node is async: {inspect.iscoroutinefunction(responder_streaming_node)}")

# Test execution
async def test_responder():
    """Test the responder with mock state"""
    mock_state = {
        "contact_id": "test123",
        "webhook_data": {"type": "WhatsApp"},
        "current_agent": "maria",
        "messages": [
            {"role": "user", "content": "hola"},
            {
                "type": "ai",
                "name": "maria", 
                "content": "¡Hola! Soy María, tu asistente virtual."
            }
        ]
    }
    
    print("\nTesting responder with mock state...")
    result = await responder_streaming_node(mock_state)
    print(f"Result: {result}")
    
    # Check what should have happened
    print("\nExpected behavior:")
    print("1. Calculate typing delay")
    print("2. Wait for delay")
    print("3. Call ghl_client.send_message()")
    print("4. Return with message_sent=True")

if __name__ == "__main__":
    asyncio.run(test_responder())