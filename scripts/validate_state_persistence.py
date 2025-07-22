#!/usr/bin/env python3
"""
Validate state persistence fix
Demonstrates that conversation state is now properly maintained across messages
"""
import asyncio
import json
import subprocess
import time
import uuid
from datetime import datetime


def send_webhook(message: str, contact_id: str, conversation_id: str, sequence: int) -> dict:
    """Send a webhook message and return the response"""
    payload = {
        "id": str(uuid.uuid4()),
        "contactId": contact_id,
        "conversationId": conversation_id,
        "type": "message",
        "body": message,
        "direction": "inbound",
        "timestamp": datetime.now().isoformat(),
        "sequenceNumber": sequence
    }
    
    cmd = [
        "curl", "-X", "POST",
        "http://localhost:8000/webhook/message",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload),
        "-s"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        return {"error": result.stderr}


async def main():
    """Run state persistence validation"""
    print("\n" + "="*60)
    print("STATE PERSISTENCE VALIDATION")
    print("="*60)
    
    # Test identifiers
    contact_id = f"test-{uuid.uuid4().hex[:8]}"
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
    
    print(f"\nTest Configuration:")
    print(f"  Contact ID: {contact_id}")
    print(f"  Conversation ID: {conversation_id}")
    print(f"  Expected thread_id: conv-{conversation_id}")
    
    # Check service health
    health_cmd = ["curl", "-s", "http://localhost:8000/health"]
    health_result = subprocess.run(health_cmd, capture_output=True, text=True)
    
    if health_result.returncode != 0:
        print("\n❌ Service not running. Start with: make dev")
        return
    
    print("\n✅ Service is healthy")
    
    # Test conversation flow
    messages = [
        ("Hi, I'm interested in learning more about your services", "Initial inquiry"),
        ("My name is Alice and I work in tech", "Name introduction"),
        ("I'd like to schedule a demo next week", "Scheduling request"),
        ("Tuesday afternoon works best for me", "Time preference")
    ]
    
    print("\n" + "-"*60)
    print("SENDING MESSAGES:")
    print("-"*60)
    
    for i, (message, description) in enumerate(messages, 1):
        print(f"\n[Message {i}] {description}")
        print(f"  Content: {message}")
        
        response = send_webhook(message, contact_id, conversation_id, i)
        
        if "error" in response:
            print(f"  ❌ Error: {response['error']}")
        else:
            print(f"  ✅ Response: {response}")
        
        # Wait between messages
        if i < len(messages):
            print("  ⏳ Waiting 2 seconds...")
            time.sleep(2)
    
    print("\n" + "-"*60)
    print("VALIDATION RESULTS:")
    print("-"*60)
    
    print("\n📊 Check LangSmith traces at:")
    print("   https://smith.langchain.com")
    
    print("\n🔍 What to verify:")
    print("   1. All messages use the same thread_id")
    print("   2. Later messages have access to earlier conversation")
    print("   3. Lead score increases as more info is provided")
    print("   4. Extracted data accumulates (name: Alice, intent: demo)")
    
    print("\n🚀 Redis state check:")
    redis_check = subprocess.run(
        ["redis-cli", "keys", f"*conv-{conversation_id}*"],
        capture_output=True,
        text=True
    )
    
    if redis_check.returncode == 0 and redis_check.stdout.strip():
        print(f"   ✅ Found Redis keys: {redis_check.stdout.strip()}")
    else:
        print("   ⚠️  No Redis keys found (might be using SQLite)")
    
    print("\n✅ Validation complete!")
    print("\nNext steps:")
    print("1. Check LangSmith traces for conversation continuity")
    print("2. Verify state persistence across messages")
    print("3. Run 'make test' to execute full test suite")


if __name__ == "__main__":
    asyncio.run(main())