#!/usr/bin/env python3
"""
Debug why conversation history is not loading
"""
import asyncio
import os
from app.tools.ghl_client import GHLClient
from app.utils.simple_logger import get_logger

logger = get_logger("debug_conversation")

async def test_conversation_loading():
    """Test conversation loading for the contact"""
    contact_id = "S0VUJbKWrwSpmHtKHlFH"
    
    print(f"\n{'='*60}")
    print(f"TESTING CONVERSATION LOADING FOR CONTACT: {contact_id}")
    print(f"{'='*60}")
    
    try:
        ghl_client = GHLClient()
        
        # Test 1: Get contact details
        print("\n1. Testing get_contact_details...")
        contact = await ghl_client.get_contact_details(contact_id)
        if contact:
            print(f"✓ Contact found: {contact.get('firstName')} {contact.get('lastName')}")
            print(f"  Email: {contact.get('email', 'none')}")
            print(f"  Phone: {contact.get('phone', 'none')}")
        else:
            print("✗ Contact not found!")
            return
        
        # Test 2: Get conversations
        print("\n2. Testing get_conversations...")
        conversations = await ghl_client.get_conversations(contact_id)
        if conversations and isinstance(conversations, list):
            print(f"✓ Found {len(conversations)} conversations")
            for i, conv in enumerate(conversations[:3]):  # Show first 3
                print(f"  [{i+1}] ID: {conv.get('id')}")
                print(f"      Type: {conv.get('type')}")
                print(f"      Last message: {conv.get('lastMessageDate')}")
        else:
            print("✗ No conversations found!")
            print(f"  Result: {conversations}")
            
        # Test 3: Get messages from first conversation
        if conversations and len(conversations) > 0:
            conv_id = conversations[0].get('id')
            print(f"\n3. Testing get_conversation_messages for conversation: {conv_id}")
            messages = await ghl_client.get_conversation_messages(conv_id)
            
            if messages and isinstance(messages, list):
                print(f"✓ Found {len(messages)} messages")
                for i, msg in enumerate(messages[:5]):  # Show first 5
                    print(f"\n  Message {i+1}:")
                    print(f"    Direction: {msg.get('direction')}")
                    print(f"    Body: {msg.get('body', '')[:100]}...")
                    print(f"    Date: {msg.get('dateAdded')}")
            else:
                print("✗ No messages found!")
                print(f"  Result: {messages}")
        
        # Test 4: Check API endpoints being called
        print("\n4. Checking API configuration...")
        print(f"  Base URL: {ghl_client.base_url}")
        print(f"  Location ID: {ghl_client.location_id}")
        print(f"  Headers: {list(ghl_client.headers.keys())}")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conversation_loading())