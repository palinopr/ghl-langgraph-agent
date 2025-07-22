#!/usr/bin/env python3
"""
Script to reproduce conversation state loss issue
Sends multiple messages to simulate a conversation and check if state persists
"""
import asyncio
import json
import time
import uuid
from datetime import datetime
import aiohttp

# Configuration
BASE_URL = "http://localhost:8000"
WEBHOOK_ENDPOINT = "/webhook/message"

# Test contact and conversation IDs
CONTACT_ID = "test-contact-" + str(uuid.uuid4())[:8]
CONVERSATION_ID = "test-conv-" + str(uuid.uuid4())[:8]


def create_webhook_payload(message: str, sequence: int):
    """Create a webhook payload simulating GoHighLevel format"""
    return {
        "id": str(uuid.uuid4()),
        "contactId": CONTACT_ID,
        "conversationId": CONVERSATION_ID,
        "type": "message",
        "body": message,
        "direction": "inbound",
        "timestamp": datetime.now().isoformat(),
        "sequenceNumber": sequence,
        "metadata": {
            "source": "test_script",
            "test_run": True
        }
    }


async def send_message(session: aiohttp.ClientSession, message: str, sequence: int):
    """Send a message webhook and return the response"""
    payload = create_webhook_payload(message, sequence)
    
    print(f"\n[{sequence}] Sending message: {message}")
    print(f"    Contact ID: {CONTACT_ID}")
    print(f"    Conversation ID: {CONVERSATION_ID}")
    
    try:
        async with session.post(
            f"{BASE_URL}{WEBHOOK_ENDPOINT}",
            json=payload
        ) as response:
        
            print(f"    Response status: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                print(f"    Response: {json.dumps(data, indent=2)}")
                return data
            else:
                text = await response.text()
                print(f"    Error: {text}")
                return None
            
    except Exception as e:
        print(f"    Exception: {e}")
        return None


async def check_langsmith_traces():
    """Print instructions for checking LangSmith traces"""
    print("\n" + "="*60)
    print("LANGSMITH TRACE VERIFICATION")
    print("="*60)
    print("\n1. Go to LangSmith Studio: https://smith.langchain.com")
    print("2. Find traces for:")
    print(f"   - Contact ID: {CONTACT_ID}")
    print(f"   - Conversation ID: {CONVERSATION_ID}")
    print("\n3. Look for these issues:")
    print("   - Different thread_ids between messages")
    print("   - Missing conversation history in later messages")
    print("   - State not being loaded from checkpoint")
    print("\n4. Check the 'receptionist' node to see if it loads previous messages")
    print("5. Check the 'thread_mapper' node to see thread_id mapping")
    print("\n" + "="*60)


async def main():
    """Run the state loss reproduction test"""
    print("\n" + "="*60)
    print("CONVERSATION STATE LOSS REPRODUCTION TEST")
    print("="*60)
    
    # Test messages simulating a real conversation
    messages = [
        "Hi, I'm interested in your services",
        "My name is John Smith and my email is john@example.com",
        "I'd like to schedule a meeting next week",
        "What times do you have available on Tuesday?"
    ]
    
    timeout = aiohttp.ClientTimeout(total=30.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # First check if service is healthy
        try:
            async with session.get(f"{BASE_URL}/health") as health:
                if health.status != 200:
                    print("ERROR: Service not healthy")
                    return
                print("✅ Service is healthy")
        except Exception as e:
            print(f"ERROR: Cannot connect to service: {e}")
            print("Make sure to run: langgraph dev --no-browser")
            return
        
        # Send messages with delays to simulate real conversation
        for i, message in enumerate(messages, 1):
            await send_message(session, message, i)
            
            if i < len(messages):
                print(f"\nWaiting 3 seconds before next message...")
                await asyncio.sleep(3)
    
    # Print trace checking instructions
    await check_langsmith_traces()
    
    print("\n✅ Test completed!")
    print(f"\nTo verify state loss, check if:")
    print("1. Each message has a different thread_id in LangSmith")
    print("2. Later messages don't have access to earlier conversation history")
    print("3. Lead score and extracted data are not carried forward")


if __name__ == "__main__":
    asyncio.run(main())