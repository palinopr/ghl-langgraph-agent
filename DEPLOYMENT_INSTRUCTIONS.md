# 🚀 Deployment Guide

This guide shows how to deploy your multi-agent system to production.

## 📋 Pre-Deployment Changes Made

✅ **Created production-ready workflow** (`app/workflow.py`)
- No complex imports that cause issues
- Full agent functionality (Maria, Carlos, Sofia)
- Thread mapping for conversation consistency
- Lead scoring and routing logic

✅ **Created production webhook handler** (`api/webhook_production.py`)
- Handles GoHighLevel webhooks
- Manages conversation history
- Integrates with LangGraph API
- Returns proper responses for GHL

✅ **Updated configuration files**
- `langgraph.json` points to production workflow
- `requirements_production.txt` with clean dependencies

## 🔧 Deployment Options

### Option 1: Deploy to LangGraph Cloud (Recommended)

```bash
# 1. Install LangGraph CLI
pip install langgraph-cli

# 2. Deploy to LangGraph Cloud
langgraph deploy

# 3. Note your deployment URL
# Example: https://your-app-id.langgraph.app
```

### Option 2: Deploy to Your Own Server

```bash
# 1. Clone repository
git clone [your-repo-url]
cd langgraph-ghl-agent

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install production dependencies
pip install -r requirements_production.txt

# 4. Set environment variables
export OPENAI_API_KEY="your-key"
export LANGSMITH_API_KEY="your-key"
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"

# 5. Start LangGraph API server
langgraph up --port 2024 &

# 6. Start webhook server
python api/webhook_production.py
```

### Option 3: Deploy with Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements_production.txt .
RUN pip install --no-cache-dir -r requirements_production.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 2024 8000

# Start both services
CMD ["sh", "-c", "langgraph up --host 0.0.0.0 --port 2024 & python api/webhook_production.py"]
```

## 🔗 GoHighLevel Configuration

1. **Get your webhook URL**:
   - LangGraph Cloud: `https://your-deployment.langgraph.app/webhook`
   - Own server: `https://your-domain.com/webhook`

2. **Configure in GoHighLevel**:
   ```
   Settings → Integrations → Webhooks → Add Webhook
   
   URL: [Your webhook URL]
   Events to subscribe:
   ✅ Inbound Message
   ✅ Outbound Message Reply
   ✅ Contact Create/Update
   ```

3. **Test the webhook**:
   - Send a test message in GHL
   - Check your server logs
   - Verify response appears in GHL

## 🗄️ Database Setup (Supabase)

Run this SQL in your Supabase dashboard:

```sql
-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    messages JSONB DEFAULT '[]'::jsonb,
    lead_score INTEGER DEFAULT 0,
    current_agent TEXT,
    last_intent TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(conversation_id)
);

-- Create indexes for performance
CREATE INDEX idx_conversations_contact_id ON conversations(contact_id);
CREATE INDEX idx_conversations_conversation_id ON conversations(conversation_id);
CREATE INDEX idx_conversations_thread_id ON conversations(thread_id);

-- Create update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_conversations_updated_at 
BEFORE UPDATE ON conversations 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();
```

## 🔐 Environment Variables

Create a `.env` file with:

```bash
# Required
OPENAI_API_KEY=sk-proj-xxxxx
LANGSMITH_API_KEY=lsv2_pt_xxxxx
LANGCHAIN_PROJECT=ghl-langgraph-agent

# GoHighLevel
GHL_API_TOKEN=pit-xxxxx
GHL_LOCATION_ID=xxxxx

# Database
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx

# Deployment
LANGGRAPH_URL=http://localhost:2024  # Change for production
WEBHOOK_SECRET=your-webhook-secret
PORT=8000
```

## 🚦 Production Checklist

Before going live:

- [ ] All environment variables set
- [ ] Database tables created
- [ ] LangGraph API running and accessible
- [ ] Webhook server running and accessible
- [ ] SSL/HTTPS configured
- [ ] GoHighLevel webhook configured
- [ ] Test message flow working
- [ ] Monitoring configured (LangSmith)
- [ ] Error alerts set up
- [ ] Backup strategy in place

## 🧪 Testing Production

1. **Test LangGraph API**:
   ```bash
   curl http://your-langgraph-url/health
   ```

2. **Test Webhook**:
   ```bash
   curl -X POST http://your-webhook-url/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "type": "InboundMessage",
       "contactId": "test-123",
       "conversationId": "conv-123",
       "locationId": "loc-123",
       "message": {
         "body": "Hola, necesito información"
       },
       "contact": {
         "firstName": "Test",
         "lastName": "User"
       }
     }'
   ```

3. **Test with real GHL message**

## 📊 Monitoring

1. **LangSmith Tracing**:
   - Go to https://smith.langchain.com
   - Select your project
   - Monitor traces in real-time

2. **Server Logs**:
   ```bash
   # LangGraph logs
   tail -f langgraph.log
   
   # Webhook logs
   tail -f webhook.log
   ```

3. **Database Queries**:
   ```sql
   -- Check recent conversations
   SELECT * FROM conversations 
   ORDER BY updated_at DESC 
   LIMIT 10;
   
   -- Check agent distribution
   SELECT current_agent, COUNT(*) 
   FROM conversations 
   GROUP BY current_agent;
   ```

## 🆘 Troubleshooting

**Issue: "No response from webhook"**
- Check webhook server is running
- Verify URL is correct in GHL
- Check firewall/security groups

**Issue: "Agent not remembering context"**
- Verify database connection
- Check conversation history is being loaded
- Ensure thread_id is consistent

**Issue: "Wrong agent routing"**
- Check lead scoring logic
- Review message content
- Verify custom fields in GHL

**Issue: "Slow responses"**
- Check server resources
- Review LangSmith traces
- Consider upgrading OpenAI tier

## 🎉 Success Indicators

Your deployment is successful when:

1. ✅ Webhook receives and processes messages
2. ✅ Correct agent responds based on lead score
3. ✅ Conversations maintain context
4. ✅ Response times are under 3 seconds
5. ✅ All traces appear in LangSmith
6. ✅ No errors in logs

## 📞 Support

If you encounter issues:

1. Check the logs first
2. Review LangSmith traces
3. Verify all environment variables
4. Test with the provided test scripts
5. Check the production test results

Remember: The system is designed to be stateless for scalability. Always send complete conversation history with each request!