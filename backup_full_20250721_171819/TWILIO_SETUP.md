# Twilio SMS Testing Setup

This guide helps you set up Twilio to send realistic SMS messages for testing your GHL webhook integration.

## Prerequisites

1. **Twilio Account**: Sign up at https://www.twilio.com
2. **Twilio Phone Number**: Purchase a number that can send SMS
3. **GHL Phone Number**: The number configured in your GHL webhook

## Installation

```bash
pip install twilio python-dotenv
```

## Configuration

Add these to your `.env` file:

```env
# Twilio Credentials (from Twilio Console)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+12345678901  # Your Twilio number

# GHL Configuration
GHL_PHONE_NUMBER=+19876543210     # Number in your GHL webhook
```

## Usage

### 1. Quick Single Message

Send a single message quickly:

```bash
# With predefined messages
python send_test_sms.py

# Or send custom message directly
python send_test_sms.py "Hola, necesito ayuda con mi negocio"
```

### 2. Realistic Conversations

Send full conversations with realistic timing:

```bash
python twilio_test_sender.py
```

This includes:
- Typing delays based on message length
- Natural pauses between messages
- Multiple conversation scenarios:
  - Spanish restaurant owner (hot lead)
  - Spanish salon owner (warm lead)
  - Spanish cold lead
  - Returning customer
  - English speaker (to test language detection)

### 3. Example Conversation Flow

The script simulates real conversations like:

```
[10:23:15] Carlos: "Hola, necesito ayuda urgente"
[10:23:22] Carlos: "Mi nombre es Carlos"  
[10:23:31] Carlos: "Tengo un restaurante"
[10:23:42] Carlos: "Estoy perdiendo clientes todos los días"
[10:23:55] Carlos: "Sí, necesito una solución ya"
[10:24:08] Carlos: "Mi presupuesto es como $500 al mes"
```

## Testing Scenarios

### Hot Lead (Spanish Restaurant Owner)
Tests:
- Spanish language processing
- Business extraction ("restaurante")
- Urgency detection ("perdiendo clientes")
- Budget confirmation flow
- Appointment booking

### Warm Lead (Spanish Salon Owner)
Tests:
- Polite Spanish conversation
- Business type extraction
- Budget discussion
- Email collection

### Cold Lead
Tests:
- Minimal information provided
- Proper routing to Maria
- Qualification questions

### Returning Customer
Tests:
- Context loading from previous conversation
- Recognition of existing customer
- Skip redundant questions

### English Speaker
Tests:
- Language detection
- Proper English responses
- Same flow in different language

## Monitoring Results

1. **Check GHL**:
   - Messages should appear in contact's conversation
   - Webhook should trigger workflow

2. **Check LangSmith Traces**:
   ```python
   from langsmith import Client
   client = Client()
   runs = list(client.list_runs(
       project_name="ghl-langgraph-agent",
       limit=10
   ))
   ```

3. **Expected Behavior**:
   - Spanish messages → Spanish responses
   - Business owners → Carlos/Sofia (score 5+)
   - Returning customers → Recognized
   - Budget confirmed → Appointment booking offered

## Troubleshooting

### "Missing Twilio configuration"
- Ensure all 4 environment variables are set in `.env`
- Check credentials in Twilio Console

### Messages not received in GHL
- Verify GHL_PHONE_NUMBER matches webhook configuration
- Check GHL workflow is active
- Ensure Twilio number has SMS capabilities

### Wrong language responses
- This was fixed in deployment (July 21, 10:04 AM)
- Check traces are post-deployment
- Verify Spanish detection is working

## Cost Considerations

- Twilio charges per SMS (usually $0.0075-$0.01)
- Test conversations use 5-9 messages each
- Monitor usage in Twilio Console

## Advanced Testing

### Custom Timing
Modify delays in `twilio_test_sender.py`:
```python
MIN_TYPING_DELAY = 2.0  # Minimum seconds
MAX_TYPING_DELAY = 8.0  # Maximum seconds
CHARS_PER_SECOND = 35   # Typing speed
```

### Add New Conversations
Add to `CONVERSATIONS` dict:
```python
"new_scenario": {
    "persona": {
        "name": "Test User",
        "scenario": "Description"
    },
    "messages": [
        "First message",
        "Second message"
    ]
}
```

### Batch Testing
The "Run all conversations" option sends all scenarios with realistic delays between different customers.

## Security Notes

- Never commit `.env` file with credentials
- Use test phone numbers in development
- Monitor Twilio usage to prevent abuse
- Consider rate limiting in production