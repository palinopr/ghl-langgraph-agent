# Real GHL Local Testing - Exact Production Environment! 🚀

## Overview
Now you can test with REAL GHL data locally:
- ✅ Real contact information
- ✅ Real conversation history  
- ✅ Real custom fields
- ✅ Real webhook processing
- ✅ Option to send real responses

## Method 1: Test with Real Contact Data (No Webhook Changes)

### Quick Test
```bash
# Test with a specific contact and message
python test_with_real_ghl.py "CONTACT_ID" "Hola"

# Interactive mode
python test_with_real_ghl.py
```

### What It Does:
1. Loads REAL contact from GHL
2. Loads REAL conversation history
3. Loads REAL custom fields
4. Processes with production workflow
5. Shows what AI would respond
6. Optionally sends response to GHL

### Example Output:
```
Testing with REAL GHL Contact
Contact ID: z49hFQn0DxOX5sInJg60
Message: tengo un negocio
==============================================================

📱 Loading contact from GHL...
✅ Contact: Maria Rodriguez
   Phone: +1234567890
   Email: maria@example.com

💬 Loading conversation history...
✅ Loaded 15 messages

Recent conversation:
   Customer: Hola
   AI: ¡Hola! Soy de Main Outlet Media...
   Customer: Maria

🔧 Enriching webhook data...
✅ Custom fields loaded: ['score', 'business_type', 'name']

🤖 Running workflow...

📊 Results:
   Extracted: {'name': 'Maria', 'business_type': None}
   Lead Score: 3
   Current Agent: maria

🤖 AI Response:
   Mucho gusto, Maria. ¿Qué tipo de negocio tienes?

==============================================================
Send this response to GHL? (y/N): n
❌ Message NOT sent (test only)
```

## Method 2: Local Server with Real Webhooks

### Setup
```bash
# Start local server that mimics production
python setup_local_ghl_testing.py
```

### Test Options:

#### Option A: Direct Testing
```bash
# Test with curl
curl -X POST http://localhost:8001/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"contactId": "YOUR_CONTACT_ID", "message": "Hola"}'

# Or use browser
http://localhost:8001/test/YOUR_CONTACT_ID/send?message=Hola
```

#### Option B: Real GHL Webhooks with ngrok
```bash
# Run the setup script
./setup_ngrok_testing.sh

# This will:
# 1. Start local server
# 2. Create ngrok tunnel
# 3. Give you a URL like: https://abc123.ngrok.io

# Update GHL webhook to: https://abc123.ngrok.io/webhook/ghl
```

Now when you send messages through GHL/WhatsApp, they'll be processed locally!

## Method 3: Production-Like Testing Script

Already exists as `run_like_production.py`:

```bash
python run_like_production.py

# Options:
# 1. Test "Restaurante" with real contact
# 2. Full conversation flow
# 3. Custom contact and message
```

## Comparison of Methods

| Method | Real Contact | Real History | Real Webhook | Can Send Response |
|--------|--------------|--------------|--------------|------------------|
| test_locally.py | ❌ | ❌ | ❌ | ❌ |
| test_with_real_ghl.py | ✅ | ✅ | ❌ | ✅ |
| setup_local_ghl_testing.py | ✅ | ✅ | ✅ | ✅ |
| Production | ✅ | ✅ | ✅ | ✅ |

## Common Testing Scenarios

### 1. Debug "negocio" Issue with Real Contact
```bash
python test_with_real_ghl.py "z49hFQn0DxOX5sInJg60" "tengo un negocio"
```

### 2. Test Full Conversation Flow
```bash
python test_with_real_ghl.py
# Choose option 2 to find a contact
# Then send multiple messages
```

### 3. Test with Live Webhooks
```bash
./setup_ngrok_testing.sh
# Update GHL webhook
# Send real messages via WhatsApp
# See processing in real-time
```

## Benefits

1. **Exact Production Replication**: Uses real data, real history
2. **No Deploy Wait**: Test changes instantly
3. **Safe Testing**: Choose whether to send responses
4. **Debug Production Issues**: Use actual contact that had problems
5. **Real-Time Testing**: With ngrok, test actual webhook flow

## Workflow

### For Bug Fixes:
1. Customer reports issue with contact X
2. Test locally: `python test_with_real_ghl.py "X" "problematic message"`
3. See the issue with real data
4. Fix the code
5. Test again with same command
6. Deploy when fixed

### For New Features:
1. Implement feature
2. Test with: `python test_with_real_ghl.py`
3. Try various contacts and messages
4. Verify behavior with real data
5. Deploy with confidence

## Important Notes

1. **Requires GHL API Access**: Make sure your `.env` has valid GHL credentials
2. **Be Careful with Send Option**: When it asks "Send to GHL?", saying "y" will ACTUALLY send the message
3. **Custom Fields**: The system will show what custom fields would be updated
4. **Rate Limits**: Be mindful of GHL API rate limits when testing

## Quick Reference

```bash
# Test specific issue with real contact
python test_with_real_ghl.py "CONTACT_ID" "message"

# Interactive testing
python test_with_real_ghl.py

# Local server for webhooks
python setup_local_ghl_testing.py

# Ngrok setup for real webhooks
./setup_ngrok_testing.sh

# Production-like testing (existing)
python run_like_production.py
```

Now you have the FULL production environment running locally! 🎉