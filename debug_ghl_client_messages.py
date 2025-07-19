#!/usr/bin/env python3
"""
Debug GHL client get_conversation_messages
"""
import asyncio
from app.tools.ghl_client import GHLClient

async def debug_ghl_client():
    """Debug what get_conversation_messages actually returns"""
    
    contact_id = "S0VUJbKWrwSpmHtKHlFH"
    ghl_client = GHLClient()
    
    print("\nDebugging GHL Client get_conversation_messages method")
    print("="*60)
    
    # Get conversations
    conversations = await ghl_client.get_conversations(contact_id)
    if conversations and len(conversations) > 0:
        conv_id = conversations[0].get('id')
        print(f"Conversation ID: {conv_id}")
        
        # Call the method directly
        print("\nCalling get_conversation_messages...")
        result = await ghl_client.get_conversation_messages(conv_id)
        
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        # Let's also check what the raw API returns
        print("\n\nChecking raw API response...")
        endpoint = f"/conversations/{conv_id}/messages"
        raw_result = await ghl_client._make_request("GET", endpoint)
        
        print(f"Raw result type: {type(raw_result)}")
        print(f"Raw result keys: {list(raw_result.keys()) if isinstance(raw_result, dict) else 'Not a dict'}")
        if isinstance(raw_result, dict) and "messages" in raw_result:
            print(f"Messages in raw result: {len(raw_result['messages'])}")
            print(f"First message: {raw_result['messages'][0] if raw_result['messages'] else 'No messages'}")

if __name__ == "__main__":
    asyncio.run(debug_ghl_client())