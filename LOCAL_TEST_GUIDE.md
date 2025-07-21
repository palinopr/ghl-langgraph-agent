# Local Testing Guide - Without ngrok Issues

Since ngrok is showing an interstitial page, here are alternative ways to test locally:

## Option 1: Use run_like_production.py (Recommended)

This script simulates production behavior with real GHL data:

```bash
python run_like_production.py
```

Choose from menu:
1. Test "Restaurante" message
2. Test full conversation flow
3. Custom contact and message

## Option 2: Direct API Testing

Start the local server:
```bash
# Terminal 1
source venv_langgraph/bin/activate
python setup_local_ghl_testing.py
```

In another terminal, test with curl:
```bash
# Terminal 2
curl -X POST http://localhost:8001/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "test123",
    "message": "Hola, tengo un restaurante",
    "body": "Hola, tengo un restaurante",
    "type": "SMS",
    "direction": "inbound",
    "locationId": "sHFG9Rw6BdGh6d6bfMqG"
  }'
```

## Option 3: Use localtunnel Instead of ngrok

Install localtunnel:
```bash
npm install -g localtunnel
```

Start tunnel:
```bash
lt --port 8001
```

This gives you a URL like: https://gentle-deer-42.loca.lt

Update GHL webhook to this URL + `/webhook/ghl`

## Option 4: Mock Testing

Create a test script that simulates GHL webhooks:

```python
import requests
import json

# Your local server must be running on port 8001
webhook_url = "http://localhost:8001/webhook/test"

# Test data
test_messages = [
    "Hola",
    "Mi nombre es Jaime",
    "Tengo un restaurante",
    "Necesito ayuda con marketing"
]

# Send messages
for msg in test_messages:
    data = {
        "contactId": "test_contact_123",
        "message": msg,
        "body": msg,
        "type": "SMS",
        "direction": "inbound",
        "locationId": "sHFG9Rw6BdGh6d6bfMqG"
    }
    
    response = requests.post(webhook_url, json=data)
    print(f"Sent: {msg}")
    print(f"Response: {response.json()}")
    print("-" * 40)
```

## What You'll See

When testing locally, you'll see:
- Incoming message processing
- Intelligence layer extraction
- Lead scoring
- Agent routing decisions
- AI responses
- Custom field updates

## Quick Start

1. **Fastest test** (no server needed):
   ```bash
   python run_like_production.py
   ```

2. **API testing** (with server):
   ```bash
   # Terminal 1
   python setup_local_ghl_testing.py
   
   # Terminal 2
   curl -X POST http://localhost:8001/webhook/test \
     -H "Content-Type: application/json" \
     -d '{"contactId": "test123", "message": "Hola"}'
   ```

## Benefits
- No ngrok issues
- Instant feedback
- Full debugging visibility
- Same workflow as production
- Can test edge cases easily