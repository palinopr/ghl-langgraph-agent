#!/usr/bin/env python3
"""
Check what messages are in GHL for this contact
"""
import asyncio
from app.tools.ghl_client import ghl_client

TEST_CONTACT_ID = "z49hFQn0DxOX5sInJg60"

async def check_messages():
    """Check messages in GHL"""
    
    print(f"🔍 Checking messages for contact {TEST_CONTACT_ID}")
    print("="*60)
    
    # Get conversation
    conversations = await ghl_client.get_conversations(TEST_CONTACT_ID)
    
    if conversations and len(conversations) > 0:
        conv = conversations[0]
        conv_id = conv['id']
        print(f"Conversation ID: {conv_id}")
        
        # Get messages
        messages = await ghl_client.get_conversation_messages(conv_id)
        
        if messages and len(messages) > 0:
            print(f"\nFound {len(messages)} messages:")
            print("-"*60)
            
            # Show last 5 messages
            for msg in messages[-5:]:
                direction = msg.get('direction', 'unknown')
                body = msg.get('body', msg.get('message', ''))[:100]
                date = msg.get('dateAdded', 'unknown')
                msg_type = msg.get('type', 'unknown')
                
                print(f"\n{direction.upper()} ({msg_type}): {body}")
                print(f"Date: {date}")
                
                # Check if it contains appointment question
                if 'agendar' in body.lower() or 'llamada' in body.lower():
                    print("⭐ Contains appointment keywords!")
            
            # Look specifically for the appointment question
            print("\n" + "="*60)
            print("Looking for appointment question...")
            found_appointment_q = False
            
            for msg in reversed(messages):
                if msg.get('direction') == 'outbound':
                    body = msg.get('body', '')
                    if 'agendar' in body.lower() and 'llamada' in body.lower():
                        print(f"\n✅ FOUND: {body}")
                        found_appointment_q = True
                        break
            
            if not found_appointment_q:
                print("❌ No appointment question found in outbound messages")
                
    else:
        print("No conversations found")

if __name__ == "__main__":
    asyncio.run(check_messages())