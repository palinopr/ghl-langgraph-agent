#!/usr/bin/env python3
"""
Debug message format in state
"""
import asyncio
from app.workflow_runner import run_workflow_safe

TEST_CONTACT_ID = "z49hFQn0DxOX5sInJg60"

async def debug_message_format():
    """Debug message format issues"""
    
    # Minimal webhook data
    webhook_data = {
        "id": TEST_CONTACT_ID,
        "contactId": TEST_CONTACT_ID,
        "message": "debug test",
        "body": "debug test",
        "type": "SMS",
        "locationId": "sHFG9Rw6BdGh6d6bfMqG",
        "direction": "inbound"
    }
    
    try:
        # Patch sofia node to print state
        import app.agents.sofia_agent_v2
        original_node = app.agents.sofia_agent_v2.sofia_node_v2
        
        async def debug_sofia_node(state):
            print("\n=== SOFIA STATE DEBUG ===")
            print(f"Messages count: {len(state.get('messages', []))}")
            
            messages = state.get('messages', [])
            for i, msg in enumerate(messages[-5:]):  # Last 5 messages
                print(f"\nMessage {i}:")
                print(f"  Type: {type(msg)}")
                print(f"  Has role attr: {hasattr(msg, 'role')}")
                print(f"  Has content attr: {hasattr(msg, 'content')}")
                if hasattr(msg, 'role'):
                    print(f"  Role: {msg.role}")
                if hasattr(msg, 'content'):
                    print(f"  Content: {msg.content[:50]}...")
                if isinstance(msg, dict):
                    print(f"  Dict keys: {list(msg.keys())}")
                    print(f"  Dict role: {msg.get('role')}")
                    print(f"  Dict content: {msg.get('content', '')[:50]}...")
            
            print("\n=== END DEBUG ===\n")
            
            # Call original
            return await original_node(state)
        
        # Temporarily replace
        app.agents.sofia_agent_v2.sofia_node_v2 = debug_sofia_node
        
        # Run workflow
        result = await run_workflow_safe(webhook_data)
        
        # Restore
        app.agents.sofia_agent_v2.sofia_node_v2 = original_node
        
        print(f"\nWorkflow result: {result.get('status')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_message_format())