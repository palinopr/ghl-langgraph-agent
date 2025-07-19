#!/usr/bin/env python3
"""
Debug the messages in state to understand their format
"""
import asyncio
from datetime import datetime
from app.workflow_runner import run_workflow_safe

TEST_CONTACT_ID = "z49hFQn0DxOX5sInJg60"

async def debug_state_messages():
    """Debug state messages"""
    
    # Customer says yes
    webhook_data = {
        "id": TEST_CONTACT_ID,
        "contactId": TEST_CONTACT_ID,
        "message": "Sí",
        "body": "Sí",
        "type": "SMS",
        "locationId": "sHFG9Rw6BdGh6d6bfMqG",
        "direction": "inbound",
        "dateAdded": datetime.now().isoformat()
    }
    
    # Patch smart responder to see what messages it gets
    import app.utils.smart_responder
    original_func = app.utils.smart_responder.get_smart_response
    
    def debug_smart_response(state, agent_name):
        print("\n=== SMART RESPONDER DEBUG ===")
        messages = state.get('messages', [])
        print(f"Total messages: {len(messages)}")
        
        # Show last 5 messages
        print("\nLast 5 messages:")
        for i, msg in enumerate(messages[-5:]):
            print(f"\nMessage {i}:")
            print(f"  Type: {type(msg).__name__}")
            
            # Check different message formats
            if hasattr(msg, 'content'):
                print(f"  Content (via attribute): '{msg.content[:100]}...'")
                if hasattr(msg, 'role'):
                    print(f"  Role (via attribute): {msg.role}")
                if hasattr(msg, 'type'):
                    print(f"  Type (via attribute): {msg.type}")
            
            if isinstance(msg, dict):
                print(f"  Dict keys: {list(msg.keys())}")
                print(f"  Content (from dict): '{msg.get('content', '')[:100]}...'")
                print(f"  Role (from dict): {msg.get('role', 'N/A')}")
            
            # Check if it's AIMessage or HumanMessage
            class_name = msg.__class__.__name__ if hasattr(msg, '__class__') else 'Unknown'
            print(f"  Class name: {class_name}")
            
            # Look for appointment keywords
            content = ""
            if hasattr(msg, 'content'):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get('content', '')
            
            if 'agendar' in content.lower() or 'llamada' in content.lower():
                print("  ⭐ Contains appointment keywords!")
        
        print("\n=== END DEBUG ===\n")
        
        # Call original
        return original_func(state, agent_name)
    
    # Replace temporarily
    app.utils.smart_responder.get_smart_response = debug_smart_response
    
    try:
        result = await run_workflow_safe(webhook_data)
        print(f"\nWorkflow result: {result.get('status')}")
    finally:
        # Restore
        app.utils.smart_responder.get_smart_response = original_func

if __name__ == "__main__":
    asyncio.run(debug_state_messages())