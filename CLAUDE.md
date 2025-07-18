# Claude Context: LangGraph GHL Agent Deployment

## Project Overview
This is a LangGraph-based GoHighLevel (GHL) messaging agent that handles intelligent lead routing and appointment booking. The system uses three AI agents (Maria, Carlos, Sofia) to handle different lead temperatures.

## Architecture

### Agent System
- **Maria** (Cold Leads, Score 1-4): Customer support, initial contact
- **Carlos** (Warm Leads, Score 5-7): Lead qualification specialist
- **Sofia** (Hot Leads, Score 8-10): Appointment booking specialist
- **Orchestrator**: Routes messages to appropriate agents based on intent

### Tech Stack
- **Framework**: LangGraph 0.3.27+ with LangChain 0.3.8+
- **API**: FastAPI with webhook endpoints
- **State Management**: LangGraph StateGraph with InMemorySaver
- **Database**: Supabase for message queue and conversation history
- **Deployment**: LangGraph Platform (LangSmith)
- **Python**: 3.11+ (required by LangGraph Platform)

## Deployment History & Issues Fixed

### Initial Deployment Attempts
1. **Render Deployment Failed**:
   - Missing `pydantic-settings` dependency
   - Config expected .env file in production
   - Wrong gunicorn app reference

2. **Railway Deployment Failed**:
   - Same dependency issues as Render
   - Railway cached old "simple app" deployment
   - Could not update to new code

### Fixed Issues

#### 1. Missing Dependencies
```python
# Added to requirements.txt:
pydantic-settings>=2.0.0  # Was missing, causing import errors
langgraph-sdk>=0.1.66     # Required for LangGraph Platform
langgraph-checkpoint>=2.0.23  # Required for persistence
```

#### 2. Configuration Issues
```python
# app/config.py - Fixed .env loading:
env_file = PROJECT_ROOT / ".env"
if env_file.exists():  # Only load if exists
    load_dotenv(env_file)
```

#### 3. Import Errors
```python
# app/workflow.py - Fixed import:
from .utils.simple_logger import get_logger  # Was importing wrong function

# app/tools/webhook_processor.py - Fixed MessageData:
# Changed from MessageData class to Dict[str, Any]
```

#### 4. Supabase Compatibility
```python
# Fixed httpx version conflict:
httpx>=0.25.0  # Was fixed at 0.25.2
supabase==2.4.0  # Works with this httpx version
```

#### 5. LangGraph Configuration
```json
// langgraph.json - Fixed format:
{
  "graphs": {
    "agent": "./app/workflow.py:workflow"  // Was object notation
  },
  "python_version": "3.11"  // Was 3.9, minimum is 3.11
}
```

#### 6. Workflow Export
```python
# app/workflow.py - Added export:
workflow = create_workflow_with_memory()  # Export for LangGraph Platform
```

#### 7. Package Name Restructuring
```bash
# LangGraph Platform doesn't allow 'src' as package name
# Changed directory structure from src/ to app/
mv src app
# Updated all imports from "from src." to "from app."
# Updated langgraph.json, vercel.json, and documentation
```

## Current Deployment Configuration

### LangGraph Platform Settings
- **Repository**: palinopr/ghl-langgraph-agent
- **Branch**: main
- **Config Path**: langgraph.json
- **Auto-deploy**: Enabled on push

### Environment Variables Required
```
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
GHL_API_TOKEN=pit-...
GHL_LOCATION_ID=xxx
GHL_CALENDAR_ID=xxx
GHL_ASSIGNED_USER_ID=xxx
```

### Dependencies (Latest Versions)
```
langgraph>=0.3.27
langchain>=0.3.8
langgraph-sdk>=0.1.66
langgraph-checkpoint>=2.0.23
langchain-core>=0.2.38
langsmith>=0.1.63
```

## Workflow Details

### Message Flow
1. Webhook receives GHL message at `/webhook/message`
2. Orchestrator analyzes intent and routes to agent
3. Selected agent processes message with specialized tools
4. Response sent back through GHL API
5. Conversation state updated in Supabase

### Routing Logic
- Keywords "appointment", "book", "schedule" → Sofia
- Keywords "business", "marketing", "services" → Carlos
- Default or general inquiries → Maria

### State Management
- Uses LangGraph StateGraph for conversation flow
- InMemorySaver for checkpointing (can upgrade to persistent)
- 30 message limit per conversation
- Automatic handoff between agents

## Common Issues & Solutions

### Build Failures
1. **Python Version**: Must be 3.11+, not 3.9
2. **Missing Dependencies**: Check requirements.txt matches latest
3. **Import Errors**: Ensure all relative imports are correct
4. **Config Format**: langgraph.json must use path:variable format

### Runtime Issues
1. **Environment Variables**: All must be set in deployment
2. **Webhook 404**: Check if correct app is deployed (not simple test app)
3. **Supabase Errors**: Verify SUPABASE_KEY is service role key

### Testing
```bash
# Health check
curl https://your-deployment.up.railway.app/health

# Test webhook
curl -X POST https://your-deployment.up.railway.app/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"type": "sms.message.inbound", "locationId": "test", ...}'
```

## Future Improvements
1. Add persistent checkpointing (DynamoDB/Redis)
2. Implement proper message queue with SQS
3. Add comprehensive logging with CloudWatch
4. Create agent performance analytics
5. Add A/B testing for agent responses

## Key Files Reference
- `app/workflow.py`: Main LangGraph workflow definition
- `app/agents/*.py`: Individual agent implementations  
- `app/api/webhook.py`: FastAPI webhook endpoints
- `app/config.py`: Settings and environment configuration
- `langgraph.json`: LangGraph Platform configuration
- `requirements.txt`: Python dependencies

## Deployment Commands
```bash
# Test locally
python main.py

# Deploy to LangGraph Platform
git add . && git commit -m "Update" && git push origin main

# Monitor deployment
# Go to https://smith.langchain.com → LangGraph Platform
```

## Support Resources
- LangGraph Docs: https://langchain-ai.github.io/langgraph/
- LangSmith Platform: https://smith.langchain.com
- GoHighLevel API: https://highlevel.stoplight.io/docs/integrations/