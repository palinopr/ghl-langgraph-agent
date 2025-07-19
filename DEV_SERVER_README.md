# 🚀 LangGraph Dev Server

A development server with detailed logging to track message flow through the workflow.

## Features
- **Real-time logging** - See exactly what's happening at each step
- **State tracking** - Monitor state changes through the workflow
- **Agent routing** - Track which agent handles each message
- **Easy log access** - View logs via web endpoints
- **Colored console output** - Easy to read logs in terminal

## Quick Start

### 1. Start the Dev Server
```bash
# Activate virtual environment
source venv_langgraph/bin/activate

# Start server
python dev_server.py
```

The server will start on `http://localhost:8000`

### 2. Send Test Messages

#### Option A: Use the Test Client
```bash
# In another terminal
python test_dev_server.py
```

Choose from:
1. **Interactive mode** - Send custom messages
2. **Test appointment flow** - Run complete appointment booking test
3. **View logs** - See all request logs

#### Option B: Send via cURL
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "test123",
    "message": "Hola",
    "type": "SMS"
  }'
```

### 3. View Logs

#### Get all requests:
```bash
curl http://localhost:8000/logs
```

#### Get specific request logs:
```bash
curl http://localhost:8000/logs/req_1234567890
```

## Log Format

Each request generates detailed logs showing:
- Webhook reception
- State initialization
- Workflow steps (Receptionist → Supervisor → Agent → Responder)
- State changes
- Final results
- AI response

## Example Output

```
[2025-07-19T15:30:00] INFO: Received webhook request
  Data: {
    "contactId": "test123",
    "message": "Hola"
  }

[2025-07-19T15:30:01] INFO: Processing message from contact: test123
  Data: {
    "contact_id": "test123",
    "message": "Hola"
  }

[2025-07-19T15:30:02] DEBUG: Step 1: receptionist
[2025-07-19T15:30:03] DEBUG: Step 2: supervisor_brain
[2025-07-19T15:30:04] DEBUG: Step 3: maria
[2025-07-19T15:30:05] DEBUG: Step 4: responder

[2025-07-19T15:30:05] SUCCESS: Workflow completed successfully
[2025-07-19T15:30:05] SUCCESS: AI Response: ¡Hola! 👋 Ayudo a las empresas...
```

## Copying Logs for Claude

1. Run your test scenario
2. Note the `request_id` from the response
3. Get the detailed logs:
   ```bash
   curl http://localhost:8000/logs/req_YOUR_ID | jq .
   ```
4. Copy the JSON output and share with Claude for analysis

## Troubleshooting

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Module not found errors
```bash
# Make sure you're in the virtual environment
source venv_langgraph/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### No response from workflow
- Check GHL API credentials in `.env`
- Verify contact ID exists in GHL
- Check console logs for errors

## Environment Variables

The dev server uses the same `.env` file as production:
- `OPENAI_API_KEY`
- `GHL_API_TOKEN`
- `GHL_LOCATION_ID`
- `LANGSMITH_API_KEY` (optional but recommended)

## Tips

1. **Use meaningful contact IDs** - Makes it easier to track conversations
2. **Check console output** - Real-time colored logs show workflow progress
3. **Save request IDs** - Useful for retrieving specific conversation logs
4. **Test edge cases** - Try incomplete data, wrong formats, etc.

## What to Look For

When debugging appointment booking:
1. Check if Sofia is selected (score 8+)
2. Verify conversation enforcer detects appointment stage
3. Look for "USE book_appointment_simple TOOL" in Sofia's prompt
4. Check the contact_id parameter in tool calls
5. Verify GHL API responses