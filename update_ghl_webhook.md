# Update GoHighLevel Webhook URL

## Steps to Update

1. **Log into GoHighLevel**
   - URL: https://app.gohighlevel.com
   - Use your admin credentials

2. **Navigate to**: Settings → Integrations → Webhooks
   
3. **Find**: Message webhook endpoint
   - Look for webhook named "LangGraph Agent" or similar
   - Should currently point to your LangGraph deployment

4. **Update URL to**:
   - From: `https://your-langgraph-deployment.com/webhook/message`
   - To: `https://your-webhook-handler.com/webhook/message`

5. **Save Changes**
   - Click "Save" or "Update"
   - Ensure webhook is enabled/active

## Test Configuration

1. **Send test message from GHL**
   ```
   Test message: "Hola, soy María y necesito ayuda"
   ```

2. **Check handler logs for**:
   ```
   "Generated thread_id: conv-123456" 
   ```
   or
   ```
   "Generated thread_id: contact-789012"
   ```

3. **Verify LangGraph Cloud receives proper thread_id**
   - Check LangSmith traces
   - Look for consistent thread_id in metadata

4. **Confirm agent remembers context between messages**
   - Send follow-up: "¿Cuál es mi nombre?"
   - Agent should respond with "María"

## Quick Test with cURL

```bash
# Test webhook handler directly
curl -X POST https://your-webhook-handler.com/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "test-123",
    "conversationId": "conv-456",
    "body": "Test message",
    "type": "Contact",
    "locationId": "loc-789"
  }'
```

## Expected Response
```json
{
  "status": "accepted",
  "thread_id": "conv-456",
  "timestamp": "2025-01-22T..."
}
```

## Rollback Plan

If issues occur:
1. Revert webhook URL to original endpoint
2. Check handler logs for errors
3. Verify environment variables are set correctly
4. Test with direct invocation endpoint first

## Monitoring

After update, monitor for:
- ✅ 200 responses from webhook handler
- ✅ Consistent thread_ids in database
- ✅ No UUID-based threads being created
- ✅ Agent maintains conversation context
- ✅ Lead scoring accumulates properly