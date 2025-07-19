#!/usr/bin/env python3
"""
Debug receptionist message loading issue
"""
import asyncio
from app.tools.ghl_client import GHLClient
from app.utils.simple_logger import get_logger

logger = get_logger("debug_messages")

async def debug_message_loading():
    """Debug the exact issue with message loading"""
    
    contact_id = "S0VUJbKWrwSpmHtKHlFH"
    ghl_client = GHLClient()
    
    print(f"\n{'='*60}")
    print("DEBUGGING MESSAGE LOADING")
    print(f"{'='*60}")
    
    try:
        # Step 1: Get conversations
        print("\n1. Getting conversations...")
        conversations = await ghl_client.get_conversations(contact_id)
        print(f"   Type of conversations result: {type(conversations)}")
        print(f"   Conversations: {conversations}")
        
        if conversations and len(conversations) > 0:
            conv_id = conversations[0].get('id')
            print(f"\n2. Getting messages for conversation: {conv_id}")
            
            # Step 2: Get messages
            conv_messages = await ghl_client.get_conversation_messages(conv_id)
            print(f"   Type of conv_messages: {type(conv_messages)}")
            print(f"   Is list?: {isinstance(conv_messages, list)}")
            print(f"   Length: {len(conv_messages) if isinstance(conv_messages, list) else 'N/A'}")
            
            if conv_messages:
                print(f"\n3. First message structure:")
                first_msg = conv_messages[0] if isinstance(conv_messages, list) and len(conv_messages) > 0 else None
                if first_msg:
                    print(f"   Keys: {list(first_msg.keys())}")
                    print(f"   Body: {first_msg.get('body', 'NO BODY')}")
                    print(f"   Direction: {first_msg.get('direction', 'NO DIRECTION')}")
                    
            # Step 3: Test the condition that's failing
            print(f"\n4. Testing receptionist condition:")
            print(f"   conv_messages is not None: {conv_messages is not None}")
            print(f"   isinstance(conv_messages, list): {isinstance(conv_messages, list)}")
            print(f"   Combined condition: {conv_messages and isinstance(conv_messages, list)}")
            
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_message_loading())