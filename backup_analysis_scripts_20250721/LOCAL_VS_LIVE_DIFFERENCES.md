# 🔍 LOCAL vs LIVE ENVIRONMENT DIFFERENCES

## Key Differences That Cause Discrepancies

### 1. **Python Dependencies**
**Local:**
- Missing packages (langsmith, httpx, etc.)
- Different versions of packages
- Using system Python vs virtual environment

**Live:**
- All dependencies pre-installed in Docker container
- Specific versions locked in requirements.txt
- Isolated environment

**Fix:**
```bash
# Install all dependencies locally
pip install -r requirements.txt
```

### 2. **Environment Variables**
**Local:**
- Loading from .env file manually
- May have different or missing values
- Not all services configured

**Live:**
- Environment variables set in LangGraph Platform
- All services properly configured
- Different API endpoints (production vs dev)

### 3. **Code Versions**
**Local:**
- Latest code with your changes
- May have uncommitted changes
- Direct file access

**Live:**
- Only deployed code from git
- May be cached or delayed deployment
- Code from specific git commit

### 4. **Data State**
**Local:**
- Testing with mock data
- Clean state each run
- No real conversation history

**Live:**
- Real GHL data
- Existing conversation history
- Previous custom fields populated
- Contact may have existing scores/tags

### 5. **Execution Environment**
**Local:**
- Running directly with Python
- Full access to filesystem
- Can modify code on the fly

**Live:**
- Running in LangGraph Platform
- Containerized environment
- Limited resources (memory/CPU)
- Timeout limits

### 6. **API Behavior**
**Local:**
- May use mock APIs
- No rate limiting
- Instant responses

**Live:**
- Real GHL API with rate limits
- Network latency
- Authentication differences
- API version differences

## How to Make Local Match Live

### 1. **Create Exact Local Environment**
```bash
# Use same Python version
python3.13 -m venv venv_live
source venv_live/bin/activate

# Install exact dependencies
pip install -r requirements.txt

# Copy exact environment variables
cp .env.production .env
```

### 2. **Load Real Data**
```python
# In test script, load actual contact data first
from app.tools.ghl_client import GHLClient

ghl = GHLClient()
contact = await ghl.get_contact_details("XinFGydeogXoZamVtZly")
conversation = await ghl.get_conversation_history("XinFGydeogXoZamVtZly")

# Use this real data in your test
initial_state = {
    "contact_info": contact,
    "conversation_history": conversation,
    "previous_custom_fields": contact.get("customFields", {})
}
```

### 3. **Match Execution Flow**
```python
# Import the exact workflow used in production
from app.workflow import workflow  # Not workflow_test or workflow_local

# Use the production configuration
from app.config import get_settings
settings = get_settings()

# Run with production settings
result = await workflow.ainvoke(
    initial_state,
    config={"configurable": {"thread_id": "production-test"}}
)
```

### 4. **Debug Deployment Differences**
```python
# Add version checking to your code
import hashlib

def get_code_hash():
    """Get hash of current code to verify deployment"""
    with open(__file__, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

logger.info(f"Code version: {get_code_hash()}")
```

### 5. **Common Issues & Solutions**

**Issue: "Module not found" locally**
```bash
# Solution: Install dependencies
pip install langsmith httpx python-dotenv
```

**Issue: Different behavior with same input**
```python
# Solution: Check initial state
logger.info(f"Initial state: {json.dumps(state, indent=2)}")
```

**Issue: API calls fail locally**
```python
# Solution: Check environment variables
import os
print("GHL_API_TOKEN present:", bool(os.getenv("GHL_API_TOKEN")))
print("GHL_CALENDAR_ID:", os.getenv("GHL_CALENDAR_ID"))
```

## Testing Script for Exact Replication

```python
#!/usr/bin/env python3
"""
Test script that exactly replicates live environment
"""
import asyncio
import os
from datetime import datetime

# 1. Load environment exactly like production
from dotenv import load_dotenv
load_dotenv()

# 2. Use production imports
from app.workflow import workflow
from app.tools.ghl_client import GHLClient

async def test_like_production():
    # 3. Load real contact data
    contact_id = "XinFGydeogXoZamVtZly"
    ghl = GHLClient()
    
    # Get current state from GHL
    contact = await ghl.get_contact_details(contact_id)
    history = await ghl.get_conversation_history(contact_id)
    
    print(f"Contact has {len(history)} messages in history")
    print(f"Current score: {contact.get('customFields', {}).get('score', 'None')}")
    
    # 4. Create webhook data like production
    webhook_data = {
        "id": contact_id,
        "contactId": contact_id,
        "message": "Restaurante",
        "body": "Restaurante",
        "type": "SMS",
        "locationId": contact.get("locationId"),
        "direction": "inbound",
        "dateAdded": datetime.now().isoformat()
    }
    
    # 5. Run through production workflow
    result = await workflow.ainvoke({
        "webhook_data": webhook_data,
        "contact_id": contact_id
    })
    
    return result

# Run test
asyncio.run(test_like_production())
```

## Why The Trace Shows Different Behavior

In your trace `1f064cd1-554a-6fd6-b196-9d317c823332`:
- **Input**: "Restaurante" 
- **Previous conversation**: Already had name "Jaime"
- **Issue**: Business type not extracted
- **Result**: Maria asks the same question again

This happens because:
1. The live environment has the OLD code (before our fix)
2. OR the extraction is failing due to message format differences
3. OR the state is not being passed correctly between nodes

## Next Steps to Debug

1. **Check deployment status**:
   - Look at deployment timestamp in LangSmith
   - Verify latest commit hash is deployed

2. **Add debug logging to see actual message**:
   ```python
   logger.info(f"Raw message type: {type(current_message)}")
   logger.info(f"Raw message content: {repr(current_message)}")
   ```

3. **Test with exact same state**:
   - Get the exact state from the failing trace
   - Run locally with that exact state
   - Compare results

The key is that **live environment has many factors** that differ from local testing, and we need to account for ALL of them to get matching behavior.