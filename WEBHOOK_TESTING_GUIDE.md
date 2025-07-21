# Real Webhook Testing - Step by Step 🚀

## What You Need:
1. Access to YOUR GHL account
2. ngrok installed (free)
3. Your local code running

## Step 1: Start Your Local Server

```bash
# Terminal 1 - Start the local GHL testing server
cd langgraph-ghl-agent
source venv_langgraph/bin/activate  # or venv313/bin/activate
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

## Step 2: Create Public URL with ngrok

```bash
# Terminal 2 - Start ngrok
ngrok http 8001
```

You'll see something like:
```
Session Status    online
Account          your-email@example.com (Plan: Free)
Version          3.3.1
Region           United States (us)
Latency          32ms
Web Interface    http://127.0.0.1:4040
Forwarding       https://abc123-45-67-89.ngrok-free.app -> http://localhost:8001
```

**COPY THE HTTPS URL!** (e.g., `https://abc123-45-67-89.ngrok-free.app`)

## Step 3: Update YOUR GHL Webhook

### In GHL:
1. Log into YOUR GoHighLevel account
2. Go to Automation → Workflows
3. Find YOUR workflow that handles incoming messages
4. Find the webhook action
5. Change the URL from:
   ```
   https://your-production.us.langgraph.app/runs/stream
   ```
   To:
   ```
   https://abc123-45-67-89.ngrok-free.app/webhook/ghl
   ```
6. Save the workflow

## Step 4: Send Test Messages

Now send a WhatsApp/SMS message to YOUR GHL phone number:
- "Hola"
- "Jaime"
- "tengo un negocio"
- etc.

## Step 5: Watch Real-Time Processing

In Terminal 1, you'll see:
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
📊 Results:
   Extracted: {'name': 'Jaime', 'business_type': None}
   Lead Score: 3
   Current Agent: maria
🤖 AI Response: Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?
```

## Step 6: The Response Goes Back to GHL!

The test server will:
1. Process the message
2. Generate the AI response
3. Send it back to GHL
4. GHL sends it to the customer via WhatsApp/SMS

## Quick Setup Script

Create `start_webhook_testing.sh`:

```bash
#!/bin/bash
echo "🚀 Starting Webhook Testing Environment"
echo "======================================"

# Start local server in background
echo "Starting local server..."
source venv_langgraph/bin/activate
python setup_local_ghl_testing.py &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Start ngrok
echo "Starting ngrok..."
ngrok http 8001 &
NGROK_PID=$!

# Wait for ngrok
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)

echo ""
echo "✅ READY FOR TESTING!"
echo "======================================"
echo "1. Update your GHL webhook to:"
echo "   $NGROK_URL/webhook/ghl"
echo ""
echo "2. Send messages via WhatsApp/SMS"
echo ""
echo "3. Watch this terminal for processing"
echo "======================================"

# Keep running until Ctrl+C
trap "kill $SERVER_PID $NGROK_PID" EXIT
wait
```

Make it executable:
```bash
chmod +x start_webhook_testing.sh
./start_webhook_testing.sh
```

## Important Notes:

1. **This uses YOUR REAL GHL account** - messages will actually be sent to customers
2. **Remember to change webhook back** when done testing
3. **ngrok URL changes** each time you restart (unless you have paid plan)
4. **You see EVERYTHING** - all processing, errors, state changes

## Monitoring Options:

### See ngrok traffic:
Open http://localhost:4040 in your browser

### See detailed logs:
The terminal shows everything:
- Incoming webhooks
- Contact data loading
- Conversation history
- AI processing
- Response generation
- What gets sent back

## When You're Done:

1. Press Ctrl+C to stop local server
2. **IMPORTANT**: Go back to GHL and restore the production webhook URL
3. Your production system continues working normally

## Benefits:

- ✅ Test with REAL messages from REAL customers
- ✅ See EXACTLY what's happening
- ✅ Fix issues without deploying
- ✅ No 20-minute wait cycles
- ✅ Full production environment locally

Now you can debug any issue in real-time! 🎉