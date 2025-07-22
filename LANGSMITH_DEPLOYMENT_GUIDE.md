# 🚀 LangSmith/LangGraph Cloud Deployment Guide

This guide shows how to deploy your GoHighLevel multi-agent system to LangGraph Cloud with LangSmith monitoring.

## 📋 Prerequisites

1. **LangSmith Account & API Key**
   ```bash
   # Get your API key from: https://smith.langchain.com/settings
   export LANGSMITH_API_KEY="lsv2_pt_xxxxx"
   ```

2. **Install LangGraph CLI**
   ```bash
   pip install -U langgraph-cli
   ```

## 🚀 Quick Deployment

### Option 1: Use the Deployment Script (Recommended)

```bash
# Run the deployment script
./deploy_to_langchain.sh
```

### Option 2: Manual Deployment

1. **Set Environment Variables**
   ```bash
   export LANGSMITH_API_KEY="your-key"
   export OPENAI_API_KEY="your-key"
   ```

2. **Deploy to LangGraph Cloud**
   ```bash
   langgraph deploy \
     --langsmith-api-key "$LANGSMITH_API_KEY" \
     --name "ghl-agent-prod"
   ```

3. **Follow the prompts to complete deployment**

## 🔗 Post-Deployment Setup

### 1. Get Your Deployment URL

After deployment, you'll receive a URL like:
```
https://your-deployment-id.graphs.langchain.com
```

### 2. Configure GoHighLevel Webhook

1. Go to GoHighLevel Settings → Integrations → Webhooks
2. Add new webhook:
   - URL: `https://your-deployment-id.graphs.langchain.com/webhook`
   - Events: Inbound Message, Outbound Message Reply

### 3. Set Production Environment Variables

In LangGraph Cloud dashboard:
1. Go to your deployment
2. Click "Environment Variables"
3. Add:
   ```
   OPENAI_API_KEY=sk-proj-xxxxx
   GHL_API_TOKEN=pit-xxxxx
   GHL_LOCATION_ID=xxxxx
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=xxxxx
   ```

## 📊 Monitoring with LangSmith

### View Traces
1. Go to https://smith.langchain.com
2. Select your project: `ghl-langgraph-agent`
3. View real-time traces

### Key Metrics to Monitor
- **Response Time**: Should be < 3 seconds
- **Agent Distribution**: Check which agents are being used
- **Error Rate**: Should be < 1%
- **Token Usage**: Monitor costs

### Setting Up Alerts
1. In LangSmith, go to Project Settings
2. Set up alerts for:
   - High latency (> 5 seconds)
   - Errors
   - Unusual token usage

## 🧪 Testing Your Deployment

### 1. Test via cURL
```bash
curl -X POST https://your-deployment-id.graphs.langchain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "type": "InboundMessage",
    "contactId": "test-123",
    "conversationId": "conv-123",
    "locationId": "loc-123",
    "message": {
      "body": "Hola, necesito información sobre marketing"
    },
    "contact": {
      "firstName": "Test",
      "lastName": "User"
    }
  }'
```

### 2. Test via GoHighLevel
Send a test message through GHL and verify:
- Message is received
- Correct agent responds
- Response appears in GHL
- Trace appears in LangSmith

## 🔧 Troubleshooting

### Deployment Fails
- Check Python version (must be 3.13)
- Verify all dependencies in requirements_production.txt
- Check LANGSMITH_API_KEY is valid

### No Traces in LangSmith
- Verify LANGCHAIN_TRACING_V2=true
- Check LANGSMITH_API_KEY in production
- Ensure LANGCHAIN_PROJECT is set

### Webhook Not Responding
- Check deployment URL is correct
- Verify webhook endpoint is /webhook
- Check logs in LangGraph Cloud dashboard

### Agent Routing Issues
- Verify lead scoring logic
- Check custom fields mapping
- Review traces for routing decisions

## 📈 Scaling Considerations

### Performance Optimization
- Use streaming responses for faster feedback
- Implement caching for common queries
- Monitor and optimize token usage

### Cost Management
- Set up spending limits in OpenAI
- Monitor token usage in LangSmith
- Use gpt-4o-mini for cost efficiency

## 🆘 Support

### LangSmith Documentation
- https://docs.smith.langchain.com

### LangGraph Documentation
- https://langchain-ai.github.io/langgraph/

### Getting Help
1. Check deployment logs
2. Review LangSmith traces
3. Contact support with trace IDs

## ✅ Production Checklist

Before going live:
- [ ] All environment variables set
- [ ] Webhook URL configured in GHL
- [ ] Test message flow working
- [ ] Traces appearing in LangSmith
- [ ] Response times < 3 seconds
- [ ] Error handling tested
- [ ] Monitoring alerts configured
- [ ] Cost limits set

## 🎉 Success!

Your multi-agent system is now deployed to LangGraph Cloud with full LangSmith monitoring!