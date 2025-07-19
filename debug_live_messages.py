#!/usr/bin/env python3
"""
Debug the actual messages in the live test
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Set up environment
os.environ['LANGSMITH_TRACING'] = 'true'
os.environ['LOG_LEVEL'] = 'INFO'

import asyncio
from datetime import datetime

async def debug_messages():
    """Debug what messages are actually being processed"""
    
    CONTACT_ID = "Emp7UWc546yDMiWVEzKF"
    
    # Import after environment setup
    from app.workflow import workflow
    from app.tools.ghl_client import GHLClient
    
    # Load conversation history
    print("Loading conversation history...")
    ghl_client = GHLClient()
    history = await ghl_client.get_conversation_history(CONTACT_ID)
    
    print(f"\n{'='*60}")
    print(f"CONVERSATION HISTORY FOR {CONTACT_ID}")
    print(f"{'='*60}")
    print(f"Total messages: {len(history)}")
    
    # Show recent messages
    for i, msg in enumerate(history[-10:]):  # Last 10 messages
        print(f"\n{i+1}. {msg['sender'].upper()} ({msg.get('timestamp', 'no time')})")
        print(f"   Message: {msg['message'][:100]}...")
        
        # Check if this is the appointment offer
        if "horarios disponibles" in msg['message'].lower():
            print("   ⭐ THIS IS THE APPOINTMENT OFFER MESSAGE")
            
    # Now run the workflow with the test message
    print(f"\n{'='*60}")
    print("RUNNING WORKFLOW WITH TEST MESSAGE")
    print(f"{'='*60}")
    
    webhook_data = {
        "id": f"msg_{int(datetime.now().timestamp())}",
        "contactId": CONTACT_ID,
        "conversationId": f"conv_{CONTACT_ID}",
        "message": "El martes a las 2pm está perfecto",
        "body": "El martes a las 2pm está perfecto",
        "type": "SMS",
        "locationId": os.getenv('GHL_LOCATION_ID', 'sHFG9Rw6BdGh6d6bfMqG'),
        "direction": "inbound",
        "dateAdded": datetime.now().isoformat()
    }
    
    initial_state = {
        "webhook_data": webhook_data,
        "contact_id": CONTACT_ID,
        "contact_info": {},
        "conversation_history": [],
        "previous_custom_fields": {},
        "messages": []
    }
    
    # Run with debug logging
    from app.utils.simple_logger import get_logger
    logger = get_logger("debug_messages")
    
    config = {
        "configurable": {
            "thread_id": f"debug-{CONTACT_ID}",
            "checkpoint_ns": ""
        }
    }
    
    result = await workflow.ainvoke(initial_state, config)
    
    # Check what messages were in the state
    print(f"\n{'='*60}")
    print("MESSAGES IN FINAL STATE")
    print(f"{'='*60}")
    
    messages = result.get('messages', [])
    print(f"Total messages in state: {len(messages)}")
    
    # Show last few messages
    for i, msg in enumerate(messages[-5:]):
        msg_type = msg.__class__.__name__ if hasattr(msg, '__class__') else type(msg)
        content = msg.content if hasattr(msg, 'content') else str(msg)[:100]
        print(f"\n{i+1}. {msg_type}")
        print(f"   Content: {content[:100]}...")
        
        # Check for appointment offer
        if hasattr(msg, 'content') and "horarios disponibles" in msg.content.lower():
            print("   ⭐ THIS IS THE APPOINTMENT OFFER IN STATE")

if __name__ == "__main__":
    asyncio.run(debug_messages())