#!/usr/bin/env python3
import asyncio
import json
from datetime import datetime
from app.tools.ghl_client import GHLClient
from app.config import get_settings
settings = get_settings()

async def debug_ghl_api():
    """Test GHL API conversation loading"""
    ghl = GHLClient()
    
    # Test with the real contact ID from GHL
    contact_id = "S0VUJbKWrwSpmHtKHlFH"  # Jaime Ortiz's actual contact ID
    
    print("=== GHL API Debug Test ===")
    print(f"Testing contact: {contact_id}")
    print(f"Using API token: {settings.ghl_api_token[:20] if settings.ghl_api_token else 'NOT SET'}...")
    print()
    
    # Test 1: Get contact info
    print("1. Testing get_contact_with_history()...")
    try:
        result = await ghl.get_contact_with_history(contact_id)
        if result and result.get('contact'):
            contact = result['contact']
            print(f"✓ Contact found: {contact.get('firstName')} {contact.get('lastName')}")
            print(f"  Email: {contact.get('email')}")
            print(f"  Phone: {contact.get('phone')}")
        else:
            print("✗ No contact found")
    except Exception as e:
        print(f"✗ Error getting contact: {e}")
    
    print("\n2. Testing get_conversations()...")
    try:
        conversations = await ghl.get_conversations(contact_id)
        if conversations:
            print(f"✓ Found {len(conversations)} conversations")
            for i, conv in enumerate(conversations[:3]):  # Show first 3
                print(f"  Conversation {i+1}: {conv.get('id')}")
                print(f"    Type: {conv.get('type')}")
                print(f"    Status: {conv.get('status')}")
                print(f"    Last message: {conv.get('lastMessageDate')}")
        else:
            print("✗ No conversations found")
            return
    except Exception as e:
        print(f"✗ Error getting conversations: {e}")
        return
    
    # Test 3: Get messages from first conversation
    if conversations and len(conversations) > 0:
        conv_id = conversations[0].get('id')
        print(f"\n3. Testing get_conversation_messages() for conversation: {conv_id}...")
        
        try:
            messages = await ghl.get_conversation_messages(conv_id)
            if messages:
                print(f"✓ Found {len(messages)} messages")
                print("\nLast 5 messages:")
                for msg in messages[-5:]:
                    direction = "← IN" if msg.get('direction') == 'inbound' else "→ OUT"
                    timestamp = msg.get('dateAdded', 'unknown')
                    body = msg.get('body', '')[:100]  # First 100 chars
                    print(f"  {direction} [{timestamp}]: {body}")
            else:
                print("✗ No messages found")
        except Exception as e:
            print(f"✗ Error getting messages: {e}")
    
    # Test 4: Check API response format
    print("\n4. Raw API Response Check...")
    try:
        # Make a direct API call to check format
        endpoint = "/conversations/search"
        params = {"contactId": contact_id, "limit": 1}
        
        result = await ghl._make_request("GET", endpoint, params=params)
        print(f"✓ Raw API response keys: {list(result.keys()) if result else 'None'}")
        
        if result and 'conversations' in result:
            conv = result['conversations'][0] if result['conversations'] else None
            if conv:
                print(f"  Conversation keys: {list(conv.keys())}")
    except Exception as e:
        print(f"✗ Error making raw request: {e}")

if __name__ == "__main__":
    asyncio.run(debug_ghl_api())