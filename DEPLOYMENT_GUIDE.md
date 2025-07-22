# DEPLOYMENT_GUIDE.md

## 🚀 LangGraph GHL Agent Deployment Guide

This guide covers everything needed to deploy the LangGraph GHL Agent to production.

## Prerequisites

- Python 3.13.5 (required for performance optimizations)
- LangSmith account and API key
- GoHighLevel API credentials
- Supabase account (optional, for message batching)

## Environment Setup

### 1. Environment Variables

Create a `.env` file with:

```bash
# Required
OPENAI_API_KEY=sk-proj-...
GHL_API_TOKEN=pit-...
GHL_LOCATION_ID=xxx
GHL_CALENDAR_ID=xxx
GHL_ASSIGNED_USER_ID=xxx

# LangSmith (Required for deployment)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ghl-langgraph-agent

# Python 3.13 Optimizations
PYTHON_GIL=0
PYTHON_JIT=1

# Optional
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
REDIS_URL=redis://localhost:6379/0
```

### 2. Python Environment

```bash
# Use Python 3.13 for production
python3.13 -m venv venv_langgraph
source venv_langgraph/bin/activate
pip install -r requirements.txt
```

## Pre-Deployment Validation

**CRITICAL**: Always validate before deployment!

```bash
# Quick validation (5 seconds)
make validate

# Full test suite (30 seconds)
make test

# What validation checks:
# ✅ Workflow imports without errors
# ✅ Workflow compiles successfully
# ✅ No circular imports
# ✅ All edges properly defined
```

## Deployment Options

### Option 1: LangGraph Platform (Recommended)

1. **Configure `langgraph.json`**:
```json
{
  "name": "ghl-langgraph-agent",
  "version": "2.0.0",
  "description": "GoHighLevel messaging agent",
  "entry_point": "app.py",
  "runtime": "python3.13"
}
```

2. **Deploy via Git Push**:
```bash
git add .
git commit -m "Deploy: your message"
git push origin main
```

3. **Monitor Deployment**:
- Check LangSmith dashboard
- Verify "Last Updated" timestamp
- Test webhook endpoint

### Option 2: Docker Deployment

```bash
# Build production image
docker build -f Dockerfile -t ghl-agent:latest .

# Run with environment variables
docker run -d \
  --name ghl-agent \
  --env-file .env \
  -p 8000:8000 \
  ghl-agent:latest
```

### Option 3: Direct Server Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run with gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Post-Deployment Verification

### 1. Health Check
```bash
curl https://YOUR-DEPLOYMENT-URL/health
# Should return: {"status": "healthy"}
```

### 2. Test Webhook
```bash
curl -X POST https://YOUR-DEPLOYMENT-URL/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "test123",
    "message": "Hola, tengo un restaurante",
    "type": "SMS"
  }'
```

### 3. Monitor Logs
- Check LangSmith traces
- Verify no errors in deployment logs
- Monitor response times

## GHL Webhook Configuration

1. **In GoHighLevel Workflow**:
   - Add "Custom Webhook" action
   - URL: `https://YOUR-DEPLOYMENT-URL/webhook/message`
   - Method: POST
   - Headers: None needed

2. **Test the Integration**:
   - Send test message through GHL
   - Check LangSmith for trace
   - Verify response in GHL

## Troubleshooting

### Common Issues

1. **"Unknown node" error**:
   - Run `make validate` before deployment
   - Check workflow edge definitions

2. **Rate limiting**:
   - GHL API has rate limits
   - Implement exponential backoff
   - Monitor rate limit headers

3. **Memory issues**:
   - Use Python 3.13 with GIL disabled
   - Enable JIT compilation
   - Monitor memory usage

### Debug Commands

```bash
# Check deployment status
curl https://YOUR-DEPLOYMENT-URL/health

# View recent errors
python fetch_trace_curl.py --errors-only

# Test specific contact
python run_like_production.py --contact-id xxx
```

## Performance Optimization

### Enable Python 3.13 Features
```bash
export PYTHON_GIL=0  # Disable GIL
export PYTHON_JIT=1  # Enable JIT
```

### Monitor Performance
```bash
curl https://YOUR-DEPLOYMENT-URL/metrics
```

## Rollback Procedure

If deployment fails:

1. **Revert to previous version**:
```bash
git revert HEAD
git push origin main
```

2. **Or manually trigger previous deployment**:
- Update version in `langgraph.json`
- Push to trigger deployment

## Security Best Practices

1. **Never commit `.env` files**
2. **Rotate API keys regularly**
3. **Use environment variables for all secrets**
4. **Enable HTTPS for all endpoints**
5. **Implement request validation**

## Monitoring & Alerts

1. **LangSmith Monitoring**:
   - Set up alerts for errors
   - Monitor trace latency
   - Track token usage

2. **Custom Metrics**:
   - Response times
   - Lead score distribution
   - Agent routing patterns

## Scaling Considerations

- Each webhook processes independently
- Use Redis for distributed message batching
- Consider horizontal scaling for high volume
- Monitor GHL API rate limits

## Quick Reference

```bash
# Validate
make validate

# Deploy
git push origin main

# Check health
curl https://YOUR-URL/health

# View logs
python fetch_trace_curl.py

# Test locally
python run_like_production.py
```

Remember: **Always validate before deploying!**