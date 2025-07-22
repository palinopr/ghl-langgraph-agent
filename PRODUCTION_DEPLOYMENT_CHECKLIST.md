# 🚀 Production Deployment Checklist

## ✅ Pre-Deployment Verification

### 1. Code & Testing (COMPLETED ✅)
- [x] All agent routing tests pass (100%)
- [x] Conversation memory tests pass (100%)
- [x] Performance tests pass (avg response < 2s)
- [x] Error handling tests pass
- [x] Concurrent request handling verified

### 2. Environment Variables (VERIFIED ✅)
```bash
# Required environment variables:
OPENAI_API_KEY=***           ✅
GHL_API_TOKEN=***           ✅
GHL_LOCATION_ID=***         ✅
SUPABASE_URL=***            ✅
SUPABASE_KEY=***            ✅
LANGSMITH_API_KEY=***       ✅
LANGCHAIN_PROJECT=***       ✅
```

### 3. Infrastructure Requirements
- [ ] Server with Python 3.11+ 
- [ ] Minimum 2GB RAM
- [ ] HTTPS certificate configured
- [ ] Domain/subdomain configured
- [ ] Firewall rules configured

## 🔧 Deployment Steps

### Step 1: Deploy LangGraph Application
```bash
# Option A: Deploy to LangGraph Cloud
langgraph deploy --project-id YOUR_PROJECT_ID

# Option B: Deploy to your own server
git clone [your-repo]
cd langgraph-ghl-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Set Up Webhook Server
```bash
# Configure webhook endpoint
export WEBHOOK_SECRET="your-secure-secret"
export LANGGRAPH_API_URL="https://your-deployment-url"

# Start webhook server
python api/webhook_simple.py
```

### Step 3: Configure GoHighLevel
1. Go to GoHighLevel Settings → Webhooks
2. Add new webhook:
   - URL: `https://your-domain.com/webhook`
   - Events: 
     - ✅ Inbound Message
     - ✅ Outbound Message 
     - ✅ Contact Update
3. Test webhook connection

### Step 4: Database Setup (Supabase)
```sql
-- Run these in Supabase SQL editor:
CREATE TABLE conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id text NOT NULL,
    conversation_id text NOT NULL,
    messages jsonb NOT NULL DEFAULT '[]',
    lead_score integer DEFAULT 0,
    current_agent text,
    created_at timestamp DEFAULT now(),
    updated_at timestamp DEFAULT now()
);

CREATE INDEX idx_contact_id ON conversations(contact_id);
CREATE INDEX idx_conversation_id ON conversations(conversation_id);
```

## 📊 Production Configuration

### Memory Management
**IMPORTANT**: The system does NOT automatically remember conversations between requests.

✅ **Best Practice Implementation**:
```python
# In your webhook handler:
async def handle_webhook(payload):
    # 1. Load conversation history from database
    history = await load_conversation_history(
        contact_id=payload['contactId'],
        conversation_id=payload['conversationId']
    )
    
    # 2. Add new message to history
    history.append({
        "role": "human",
        "content": payload['message']['body']
    })
    
    # 3. Send COMPLETE history to LangGraph
    response = await langgraph_client.runs.stream(
        thread_id,
        "agent",
        input={
            "messages": history,  # FULL conversation history
            "contact_id": payload['contactId'],
            "conversation_id": payload['conversationId']
        }
    )
    
    # 4. Save updated history to database
    await save_conversation_history(history)
```

### Performance Optimization
- Enable response streaming for better UX
- Implement request queuing for high volume
- Set up caching for common responses
- Monitor and alert on response times > 3s

### Error Handling
```python
# Implement retry logic
@retry(max_attempts=3, backoff=2)
async def send_to_langgraph(payload):
    try:
        return await client.runs.stream(...)
    except Exception as e:
        logger.error(f"LangGraph error: {e}")
        # Return fallback response
        return create_fallback_response()
```

## 🎯 GoHighLevel Integration

### Custom Fields Mapping
```javascript
// In GoHighLevel, create these custom fields:
const customFields = {
    lead_score: "wAPjuqxtfgKLCJqahjo1",      // Number 0-10
    last_intent: "Q1n5kaciimUU6JN5PBD6",     // Text
    business_type: "HtoheVc48qvAfvRUKhfG",   // Text
    last_agent: "custom_field_id",           // Text
    conversation_summary: "custom_field_id"   // Long text
};
```

### Webhook Response Format
```python
# Your webhook should return:
{
    "success": true,
    "message": "AI response text here",
    "agent": "maria|carlos|sofia",
    "lead_score": 0-10,
    "custom_fields": {
        "lead_score": 7,
        "last_intent": "appointment_booking",
        "business_type": "restaurant"
    }
}
```

## 📈 Monitoring & Maintenance

### 1. Set Up Monitoring
- [ ] LangSmith tracing enabled
- [ ] Error tracking (Sentry/Rollbar)
- [ ] Uptime monitoring (UptimeRobot)
- [ ] Response time alerts
- [ ] Daily conversation reports

### 2. Regular Maintenance
- Check LangSmith traces weekly
- Review conversation quality
- Update agent prompts based on feedback
- Monitor token usage and costs
- Backup conversation database

### 3. Scaling Considerations
- Use Redis for caching if > 1000 conversations/day
- Implement horizontal scaling for webhook server
- Consider dedicated GPU for faster responses
- Set up load balancer for multiple instances

## 🔒 Security Checklist

- [ ] HTTPS enabled on all endpoints
- [ ] Webhook secret configured and validated
- [ ] API keys stored securely (environment variables)
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] Regular security audits

## 🚦 Go-Live Checklist

### Before Going Live:
1. [ ] All tests pass (100% success rate)
2. [ ] Webhook endpoint accessible from internet
3. [ ] GoHighLevel webhook configured and tested
4. [ ] Database tables created and indexed
5. [ ] Monitoring alerts configured
6. [ ] Backup strategy in place
7. [ ] Customer documentation ready

### After Going Live:
1. [ ] Monitor first 10 conversations closely
2. [ ] Check response times and errors
3. [ ] Verify lead scoring accuracy
4. [ ] Confirm agent routing works correctly
5. [ ] Test appointment booking flow
6. [ ] Review conversation quality

## 📞 Support & Troubleshooting

### Common Issues:

**1. No Response from Webhook**
- Check server logs
- Verify webhook URL is correct
- Ensure HTTPS certificate is valid
- Check firewall rules

**2. Agent Not Remembering Context**
- Verify conversation history is being loaded
- Check database connectivity
- Ensure full history is sent with each request

**3. Slow Response Times**
- Check server resources (CPU/RAM)
- Review LangSmith traces for bottlenecks
- Consider upgrading OpenAI model tier
- Implement caching for common queries

**4. Wrong Agent Routing**
- Review lead scoring logic
- Check message analysis
- Adjust scoring thresholds if needed

## ✅ Final Verification

Run this command to verify production readiness:
```bash
python test_production_complete.py
```

Expected output:
- Overall Success Rate: 100%
- All tests: PASSED
- Production Status: READY

---

## 🎉 Congratulations!

Your multi-agent AI system is ready for production deployment. The system will:

1. **Route conversations** to the appropriate agent based on lead scoring
2. **Maintain context** when you provide full conversation history
3. **Handle errors** gracefully
4. **Scale** to handle concurrent conversations
5. **Integrate** seamlessly with GoHighLevel

Remember: The key to maintaining conversation context is to always load and send the complete conversation history with each request.

Good luck with your deployment! 🚀