# Live Testing Guide for GHL LangGraph Agent

## Overview
This guide explains how to perform live end-to-end testing by creating real GHL contacts and sending messages through the API.

## Test Scripts

### 1. `test_ghl_live_api.py` - Direct GHL API Testing
Creates contacts and sends messages directly through GHL API.

**Features:**
- Creates unique test contacts with timestamps
- Simulates different conversation types (appointment, qualification, support)
- Sends messages with natural delays
- Tracks contact IDs for verification

**Usage:**
```bash
python test_ghl_live_api.py
```

**Menu Options:**
1. Appointment booking flow (Hot lead)
2. Qualification flow (Warm lead)
3. Support request (Cold lead)
4. Exploratory questions (Cold lead)
5. Custom messages

### 2. `test_ghl_webhook_integration.py` - Complete Integration Testing
Tests the full flow: GHL → Webhook → Workflow → GHL Updates

**Features:**
- Creates test contacts
- Simulates webhook calls
- Verifies custom field updates
- Checks lead scoring
- Cleans up test data

**Usage:**
```bash
# First, start your local webhook server
python app.py

# In another terminal, run the integration test
python test_ghl_webhook_integration.py
```

## GHL API Operations

### Creating a Contact
```python
contact_data = {
    "firstName": "Test",
    "lastName": "User",
    "email": "test@example.com",
    "phone": "+15551234567",
    "source": "API Test",
    "tags": ["test-contact"],
    "customFields": [
        {
            "id": "field_id_here",
            "value": "field_value"
        }
    ]
}

# POST /contacts/
response = await client.post(
    "https://api.gohighlevel.com/contacts/",
    headers={
        "Authorization": f"Bearer {api_token}",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    },
    json={
        "locationId": location_id,
        **contact_data
    }
)
```

### Sending a Message
```python
# First create/get conversation
conversation_data = {
    "locationId": location_id,
    "contactId": contact_id
}

conv_response = await client.post(
    "https://api.gohighlevel.com/conversations/",
    headers=headers,
    json=conversation_data
)

# Then send message
message_data = {
    "type": "SMS",  # or "Email"
    "contactId": contact_id,
    "conversationId": conversation_id,
    "message": "Your message here",
    "conversationProviderId": "leadconnector"  # for SMS
}

response = await client.post(
    "https://api.gohighlevel.com/conversations/messages",
    headers=headers,
    json=message_data
)
```

## Test Scenarios

### 1. Hot Lead - Appointment Booking
```python
messages = [
    "Hola",
    "Mi nombre es Juan Carlos",
    "Tengo un restaurante",
    "Necesito automatizar las reservas",
    "Sí, $300 está bien",
    "juan@mirestaurante.com",
    "10:00 AM"
]
```
**Expected:** Lead score 8-10, appointment booked

### 2. Warm Lead - Qualification
```python
messages = [
    "Hi, I need help",
    "My name is Sarah",
    "I run an online boutique",
    "I want to automate customer support",
    "What's the investment?",
    "Yes, that works",
    "sarah@boutique.com"
]
```
**Expected:** Lead score 5-7, routed to Carlos

### 3. Cold Lead - Support
```python
messages = [
    "Necesito ayuda",
    "Mi sistema no funciona",
    "No puedo acceder a mi cuenta",
    "Mi email es test@example.com"
]
```
**Expected:** Lead score 1-4, routed to Maria

## Verification Checklist

### After Running Tests:

1. **Check GHL Contact:**
   - Custom fields updated (score, intent, business_type, etc.)
   - Tags applied (hot-lead, warm-lead, etc.)
   - Conversation history recorded

2. **Check LangSmith Traces:**
   - Workflow execution path
   - Agent decisions
   - Tool calls
   - Score calculations

3. **Check Application Logs:**
   - Webhook processing
   - Intelligence analysis
   - Agent routing
   - GHL API calls

4. **Check Response Times:**
   - Webhook response < 5s
   - Message batching working
   - No timeouts

## Common Issues & Solutions

### Issue: "Failed to create contact"
- Check GHL API token permissions
- Verify location ID is correct
- Ensure required fields are provided

### Issue: "Failed to send message"
- Contact must exist first
- Conversation must be created
- Check conversationProviderId for SMS

### Issue: "Webhook timeout"
- Ensure local server is running
- Check webhook URL (default: localhost:8000)
- Verify no firewall blocking

### Issue: "Custom fields not updating"
- Check field IDs in FIELD_MAPPINGS
- Verify API token has write permissions
- Check GHL API response for errors

## Best Practices

1. **Use Unique Data:**
   - Always use timestamps in test data
   - Avoid reusing email/phone numbers
   - Tag test contacts for easy filtering

2. **Clean Up Test Data:**
   - Tag contacts with "DELETE-ME" for cleanup
   - Keep track of created contact IDs
   - Run cleanup after tests

3. **Test Incrementally:**
   - Start with contact creation
   - Test single messages first
   - Build up to full conversations

4. **Monitor in Real-Time:**
   - Watch application logs while testing
   - Check LangSmith traces immediately
   - Verify GHL updates after each step

## Environment Setup

Required environment variables:
```bash
# GHL Configuration
GHL_API_TOKEN=pit-...
GHL_LOCATION_ID=...
GHL_CALENDAR_ID=...
GHL_ASSIGNED_USER_ID=...

# OpenAI
OPENAI_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...

# LangSmith (optional but recommended)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ghl-langgraph-agent
```

## Advanced Testing

### Custom Message Flows
```python
# Create your own test scenarios
custom_flow = [
    "¿Qué servicios ofrecen?",
    "Me interesa la automatización",
    "Mi nombre es Pedro",
    "Tengo una agencia de viajes",
    # Add more messages...
]
```

### Parallel Testing
```python
# Test multiple contacts simultaneously
async def parallel_test():
    tasks = []
    for i in range(3):
        task = create_and_test_contact(f"Test User {i}")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
```

### Performance Testing
```python
# Measure response times
start_time = time.time()
await simulate_webhook_message(contact_id, message)
response_time = time.time() - start_time
logger.info(f"Response time: {response_time:.2f}s")
```

## Summary

These testing tools allow you to:
- ✅ Create real GHL contacts via API
- ✅ Send messages through proper channels
- ✅ Test complete workflow execution
- ✅ Verify data persistence
- ✅ Validate agent behavior
- ✅ Check performance metrics

Use these scripts to ensure your deployment is working correctly before going live!