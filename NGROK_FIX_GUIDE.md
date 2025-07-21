# Fix for ngrok Interstitial Page Issue

## The Problem
GHL webhooks are failing with HTML error because ngrok shows a warning page for free accounts.

## Solution Options

### Option 1: Add ngrok-skip-browser-warning Header (Recommended)
In your GHL webhook configuration, add this header:
```
ngrok-skip-browser-warning: true
```

### Option 2: Use ngrok with Authentication
Start ngrok with basic auth to bypass the warning:
```bash
ngrok http 8001 --auth="username:password"
```
Then include the auth in your webhook URL:
```
https://username:password@abc123.ngrok.io/webhook/ghl
```

### Option 3: Use Alternative - localtunnel
Install and use localtunnel instead:
```bash
npm install -g localtunnel
lt --port 8001 --subdomain yourname
```
This gives you: https://yourname.loca.lt

### Option 4: Test Directly Without GHL
While ngrok is running, test your local endpoint directly:

```bash
# Get your ngrok URL first
curl http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4

# Then test directly
curl -X POST https://YOUR-NGROK-URL/webhook/ghl \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{
    "contactId": "z49hFQn0DxOX5sInJg60",
    "message": "Hola",
    "body": "Hola",
    "type": "SMS",
    "direction": "inbound",
    "locationId": "sHFG9Rw6BdGh6d6bfMqG"
  }'
```

## Quick Test Without GHL

Since you have the server running on port 8001, you can test directly:

### 1. Test with curl (no ngrok needed)
```bash
curl -X POST http://localhost:8001/webhook/test \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "z49hFQn0DxOX5sInJg60",
    "message": "tengo un negocio",
    "body": "tengo un negocio",
    "type": "SMS",
    "direction": "inbound",
    "locationId": "sHFG9Rw6BdGh6d6bfMqG"
  }'
```

### 2. Use the test script directly
```bash
python test_with_real_ghl.py "z49hFQn0DxOX5sInJg60" "tengo un negocio"
```

This bypasses GHL and ngrok completely while still testing with real data!

## Recommended Approach

For immediate testing without dealing with ngrok issues:
1. Keep your local server running (port 8001)
2. Use the curl commands above to test
3. Or use `test_with_real_ghl.py` for interactive testing
4. You'll see all the same processing, just without the webhook layer