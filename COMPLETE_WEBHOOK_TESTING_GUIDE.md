# Complete Webhook Testing Guide - Test Locally with Real GHL! 🚀

## Overview
This guide shows you ALL the ways to test your agent locally with real GHL data, eliminating the painful 20-minute deploy cycles.

## Quick Start (30 seconds)

### Option 1: Test with Real Contact (No Webhook Changes)
```bash
# Test specific contact with message
python test_with_real_ghl.py "CONTACT_ID" "Hola"

# Interactive mode
python test_with_real_ghl.py
```

### Option 2: Real Webhooks with ngrok
```bash
# Run this single command
./setup_ngrok_testing.sh

# You'll get a URL like: https://abc123.ngrok.io
# Update GHL webhook to: https://abc123.ngrok.io/webhook/ghl
# Send real messages via WhatsApp/SMS!
```

## Method 1: Direct Contact Testing (test_with_real_ghl.py)

### What It Does
- Loads REAL contact from YOUR GHL
- Loads REAL conversation history
- Processes with production workflow
- Shows AI response
- Optionally sends to GHL

### Usage Examples

#### Test Specific Issue
```bash
# Customer having "negocio" issue
python test_with_real_ghl.py "z49hFQn0DxOX5sInJg60" "tengo un negocio"

# Customer name being asked again
python test_with_real_ghl.py "z49hFQn0DxOX5sInJg60" "Jaime"
```

#### Interactive Testing
```bash
python test_with_real_ghl.py

# Menu:
# 1. Test with specific contact ID
# 2. Find a contact to test with  
# 3. Quick test (contact:message)
# 4. Exit

# Choose 2 to see your recent contacts
# Pick one and test various messages
```

### Example Output
```
Testing with REAL GHL Contact
Contact ID: z49hFQn0DxOX5sInJg60
Message: tengo un negocio
==============================================================

📱 Loading contact from GHL...
✅ Contact: Jaime Rodriguez
   Phone: +1234567890

💬 Loading conversation history...
✅ Loaded 23 messages

Recent conversation:
   Customer: Hola
   AI: ¡Hola! Soy de Main Outlet Media...
   Customer: Jaime

🤖 Running workflow...

📊 Results:
   Extracted: {'name': 'Jaime', 'business_type': None}
   Lead Score: 3
   Current Agent: maria

🤖 AI Response:
   Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?

Send this response to GHL? (y/N): n
```

## Method 2: Local Server with Real Webhooks

### Step 1: Start Local Server
```bash
python setup_local_ghl_testing.py
```

You'll see:
```
🚀 Starting Local GHL Testing Server
==================================
✅ Loads real contact data from GHL
✅ Loads real conversation history
✅ Uses actual webhook enrichment
✅ Processes with production workflow
==================================
Server running at: http://localhost:8001
```

### Step 2: Set Up ngrok Tunnel
```bash
# In new terminal
ngrok http 8001
```

Copy the HTTPS URL (like `https://abc123.ngrok.io`)

### Step 3: Update GHL Webhook

1. Log into YOUR GHL account
2. Go to Automation → Workflows
3. Find your message handling workflow
4. Change webhook URL from:
   ```
   https://your-production.us.langgraph.app/runs/stream
   ```
   To:
   ```
   https://abc123.ngrok.io/webhook/ghl
   ```
5. Save workflow

### Step 4: Send Real Messages!
- Send WhatsApp/SMS to your GHL number
- Watch processing in real-time in terminal
- See EXACTLY what happens

## Method 3: One-Command Setup

### Create setup_ngrok_testing.sh
```bash
#!/bin/bash
echo "🚀 Setting up ngrok for GHL webhook testing"

# Start local server
python setup_local_ghl_testing.py &
SERVER_PID=$!
sleep 3

# Start ngrok
ngrok http 8001 &
NGROK_PID=$!
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")

echo "✅ Setup complete!"
echo "Update GHL webhook to: $NGROK_URL/webhook/ghl"

trap "kill $SERVER_PID $NGROK_PID" EXIT
wait
```

### Run It
```bash
chmod +x setup_ngrok_testing.sh
./setup_ngrok_testing.sh
```

## Testing Different Scenarios

### 1. Debug Repeated Questions
```bash
# First message
python test_with_real_ghl.py "CONTACT_ID" "Hola"
# See response, then:
python test_with_real_ghl.py "CONTACT_ID" "Jaime"
# Should NOT ask for name again
```

### 2. Test Typo Tolerance
```bash
python test_with_real_ghl.py "CONTACT_ID" "tengo un restorante"
# Should recognize "restorante" as "restaurante"
```

### 3. Test Business Extraction
```bash
python test_with_real_ghl.py "CONTACT_ID" "tengo un negocio de comida"
# Should extract "restaurante" not generic "negocio"
```

### 4. Full Conversation Flow
```bash
# Use webhook method for realistic timing
./setup_ngrok_testing.sh
# Update GHL webhook
# Send multiple messages via WhatsApp
```

## Quick Test Endpoints

When running `setup_local_ghl_testing.py`:

### Browser Test
```
http://localhost:8001/test/CONTACT_ID/send?message=Hola
```

### curl Test
```bash
curl -X POST http://localhost:8001/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"contactId": "CONTACT_ID", "message": "Hola"}'
```

## What You See in Real-Time

```
Received GHL webhook: {
  "contactId": "z49hFQn0DxOX5sInJg60",
  "message": "tengo un negocio",
  "type": "SMS",
  ...
}
📱 Loading contact from GHL...
✅ Contact: Jaime Rodriguez
💬 Loading conversation history...
✅ Loaded 23 messages
🤖 Running workflow...
   [Intelligence] Analyzing: "tengo un negocio"
   [Intelligence] Current state: {'name': 'Jaime'}
   [Intelligence] Extracted: {'business_type': None}
   [Supervisor] Score: 3, Agent: maria
   [Maria] Generating response...
📊 Results:
   Response: "Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"
✅ Would send to GHL
```

## Troubleshooting

### ngrok not installed?
```bash
# macOS
brew install ngrok/ngrok/ngrok

# Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### GHL API errors?
Check your `.env` file:
```
GHL_API_KEY=your_key
GHL_LOCATION_ID=your_location
GHL_ASSIGNED_USER_ID=your_user
```

### Webhook not working?
1. Check ngrok is running: http://localhost:4040
2. Verify GHL webhook URL updated
3. Check workflow is active in GHL

## Best Practices

### For Bug Fixes
1. Get problematic contact ID from user
2. Test locally: `python test_with_real_ghl.py "ID" "problematic message"`
3. Fix the issue
4. Test again with same command
5. Deploy when verified

### For New Features
1. Use `test_with_real_ghl.py` in interactive mode
2. Test with multiple contacts
3. Verify with webhook method for timing
4. Deploy with confidence

### Daily Development
1. Always test locally first
2. Use real contact data
3. Verify with webhook method before deploy
4. Keep ngrok running during development

## Summary

You now have THREE ways to test:

1. **Direct Testing** (`test_with_real_ghl.py`)
   - Best for: Specific issues, quick tests
   - Real data: ✅ Contact, ✅ History
   - Speed: Instant

2. **Local Server** (`setup_local_ghl_testing.py`)
   - Best for: Full webhook testing
   - Real data: ✅ Everything
   - Speed: Real-time

3. **One Command** (`setup_ngrok_testing.sh`)
   - Best for: Daily development
   - Real data: ✅ Everything
   - Speed: One command setup

No more 20-minute deploy cycles! Test everything locally with real data! 🎉

## Quick Reference Card

```bash
# Test specific issue
python test_with_real_ghl.py "CONTACT_ID" "message"

# Interactive testing
python test_with_real_ghl.py

# Full webhook testing
./setup_ngrok_testing.sh

# Manual server + ngrok
python setup_local_ghl_testing.py  # Terminal 1
ngrok http 8001                    # Terminal 2

# Quick browser test
http://localhost:8001/test/CONTACT_ID/send?message=Hola
```

Remember:
- These use YOUR REAL GHL account
- Messages CAN be sent to real customers (you choose)
- Always restore production webhook when done
- ngrok URLs change on restart (unless paid)

Happy testing! 🚀