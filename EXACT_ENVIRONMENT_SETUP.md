# 🎯 EXACT Environment Setup - Match LangGraph Production

## Overview
This guide shows how to create a LOCAL environment that behaves EXACTLY like the LangGraph production deployment.

## Method 1: Quick Setup (Recommended)

### 1. Install Python 3.13
```bash
# macOS
brew install python@3.13

# Ubuntu/Debian
sudo apt update
sudo apt install python3.13 python3.13-venv

# Verify
python3.13 --version  # Should show 3.13.x
```

### 2. Run Setup Script
```bash
# Make executable
chmod +x setup_exact_environment.sh

# Run setup
./setup_exact_environment.sh
```

This script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install exact dependencies
- ✅ Verify environment setup

### 3. Activate Environment
```bash
source venv_langgraph/bin/activate
```

### 4. Run Like Production
```bash
python run_like_production.py
```

## Method 2: Docker (Most Accurate)

### 1. Build Docker Image
```bash
# Build image matching LangGraph
docker build -f Dockerfile.local -t langgraph-local .
```

### 2. Run Container
```bash
# Run with environment variables
docker run -it --rm \
  --env-file .env \
  -p 8000:8000 \
  langgraph-local
```

## Method 3: Manual Setup

### 1. Create Virtual Environment
```bash
# MUST use Python 3.13
python3.13 -m venv venv_exact
source venv_exact/bin/activate
```

### 2. Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install exact requirements
pip install -r requirements.txt

# Install additional packages used in production
pip install langsmith httpx python-dotenv aiohttp tenacity orjson
```

### 3. Set Environment Variables
```bash
# Copy from .env
export OPENAI_API_KEY="your-key"
export GHL_API_TOKEN="your-token"
export GHL_LOCATION_ID="your-location"
export GHL_CALENDAR_ID="your-calendar"
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"

# LangSmith settings (like production)
export LANGSMITH_TRACING=true
export LANGCHAIN_TRACING_V2=true
export LANGSMITH_PROJECT=ghl-langgraph-agent
export LOG_LEVEL=INFO
```

### 4. Test Environment
```python
# Run this to verify setup
from app.workflow import workflow
from app.tools.ghl_client import GHLClient
from app.agents.supervisor_brain_simple import supervisor_brain_simple_node

print("✅ All imports working!")
```

## Key Differences to Account For

### 1. **Import Order Matters**
```python
# Production loads environment FIRST
import os
os.environ['LANGSMITH_TRACING'] = 'true'

# THEN imports modules
from app.workflow import workflow
```

### 2. **State Initialization**
Production always starts with:
```python
{
    "webhook_data": {...},
    "contact_id": "...",
    "contact_info": {},  # Empty, filled by receptionist
    "conversation_history": [],  # Empty, filled by receptionist
    "previous_custom_fields": {},  # Empty, filled by receptionist
    "messages": []  # Empty initially
}
```

### 3. **Workflow Configuration**
```python
# Production uses specific config
config = {
    "configurable": {
        "thread_id": "unique-thread-id",
        "checkpoint_ns": ""
    },
    "metadata": {
        "source": "webhook",
        "contact_id": contact_id
    }
}
```

### 4. **API Endpoints**
- Local might use mock endpoints
- Production uses: `https://services.leadconnectorhq.com`
- API version: `2021-07-28`

## Testing Production Behavior

### 1. Test Single Message
```bash
python run_like_production.py
# Choose option 1
# Tests single "Restaurante" message
```

### 2. Test Full Conversation
```bash
python run_like_production.py
# Choose option 2
# Tests complete flow from greeting to appointment
```

### 3. Debug Specific Issue
```python
# Create test for exact scenario
from app.workflow import workflow

# Load REAL contact data
contact_id = "XinFGydeogXoZamVtZly"
message = "Restaurante"

# Run through production workflow
result = await workflow.ainvoke({
    "webhook_data": {
        "contactId": contact_id,
        "message": message,
        ...
    }
})
```

## Verifying Environment Matches

### 1. Check Versions
```bash
# In your environment
pip freeze | grep -E "langchain|langgraph|openai"

# Should match requirements.txt exactly
```

### 2. Check Behavior
- Business extraction should work for "Restaurante"
- Score should increment properly
- Routing should go to correct agent
- API calls should succeed

### 3. Check Logs
Production logs will show:
```
🚀 DEPLOYMENT INFO
  - Version: 1.2.0
  - Features:
    ✓ Enhanced business extraction for single words
```

## Common Issues & Solutions

### Issue: Import Errors
```bash
# Solution: Install missing packages
pip install langsmith httpx python-dotenv
```

### Issue: Different Behavior
```python
# Solution: Load real GHL data
ghl = GHLClient()
contact = await ghl.get_contact_details(contact_id)
history = await ghl.get_messages(contact_id)
```

### Issue: API Failures
```bash
# Solution: Check environment variables
env | grep GHL_
env | grep OPENAI_
```

## Production Debugging Checklist

- [ ] Using Python 3.13
- [ ] All dependencies installed from requirements.txt
- [ ] Environment variables loaded from .env
- [ ] Using production workflow (not test versions)
- [ ] Loading real GHL data (not mocks)
- [ ] LangSmith tracing enabled
- [ ] LOG_LEVEL set to INFO (not DEBUG)
- [ ] Running with proper async context

## Summary

To match production EXACTLY:
1. Use Python 3.13
2. Install exact dependencies
3. Load real GHL data
4. Use production workflow
5. Set all environment variables
6. Run with proper configuration

The `run_like_production.py` script handles all of this automatically!