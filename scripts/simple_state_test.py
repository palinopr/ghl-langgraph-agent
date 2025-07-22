#!/usr/bin/env python3
"""
Simple script to test state persistence using curl commands
"""
import subprocess
import json
import time
import uuid

# Test IDs
CONTACT_ID = "test-contact-" + str(uuid.uuid4())[:8]
CONVERSATION_ID = "test-conv-" + str(uuid.uuid4())[:8]

print(f"\nTesting with:")
print(f"Contact ID: {CONTACT_ID}")
print(f"Conversation ID: {CONVERSATION_ID}")
print("\n" + "="*60)

# Test messages
messages = [
    "Hi, I'm interested in your services",
    "My name is John Smith and my email is john@example.com",
    "I'd like to schedule a meeting next week",
    "What times do you have available on Tuesday?"
]

for i, message in enumerate(messages, 1):
    payload = {
        "id": str(uuid.uuid4()),
        "contactId": CONTACT_ID,
        "conversationId": CONVERSATION_ID,
        "type": "message",
        "body": message,
        "direction": "inbound",
        "timestamp": time.time(),
        "sequenceNumber": i
    }
    
    print(f"\n[Message {i}] Sending: {message}")
    
    # Use curl to send the request
    curl_cmd = [
        "curl", "-X", "POST",
        "http://localhost:8000/webhook/message",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload),
        "-s"
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Response: {result.stdout}")
        else:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed to send: {e}")
    
    # Wait between messages
    if i < len(messages):
        print("Waiting 3 seconds...")
        time.sleep(3)

print("\n" + "="*60)
print("TEST COMPLETE")
print("\nCheck LangSmith traces for:")
print(f"- Contact ID: {CONTACT_ID}")
print(f"- Conversation ID: {CONVERSATION_ID}")
print("\nLook for:")
print("1. Different thread_ids between messages")
print("2. Missing conversation history")
print("3. State not persisting")