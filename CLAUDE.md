# Claude Context: LangGraph GHL Agent - Complete Implementation Guide

## Project Overview
This is a LangGraph-based GoHighLevel (GHL) messaging agent that handles intelligent lead routing and appointment booking. The system uses three AI agents (Maria, Carlos, Sofia) orchestrated by a supervisor using the latest LangGraph patterns with advanced features like message batching, intelligent scoring, and full conversation context loading.

## Architecture Evolution

### Original Architecture (v1)
- **Maria** (Cold Leads, Score 1-4): Customer support, initial contact
- **Carlos** (Warm Leads, Score 5-7): Lead qualification specialist
- **Sofia** (Hot Leads, Score 8-10): Appointment booking specialist
- **Orchestrator**: Routes messages to appropriate agents based on intent

### Modernized Architecture (v2) - 2025-07-18
- **Supervisor**: Central orchestrator using `create_react_agent` pattern
- **Maria**: Support agent with handoff capabilities via Command objects
- **Carlos**: Qualification agent with state-aware tools
- **Sofia**: Appointment agent with direct booking and memory integration
- **Memory Store**: Semantic search and conversation persistence

### Enhanced Architecture (v3) - CURRENT (2025-07-18)
- **Intelligence Layer**: Pre-processing analysis inspired by n8n workflow
  - Spanish pattern extraction (names, business, budget)
  - Deterministic lead scoring (1-10 scale)
  - Budget confirmation detection
  - Score persistence (never decreases)
- **Supervisor**: Enhanced with score-based routing rules
- **Agents**: Same as v2 but now receive enriched state
- **Flow**: Message → Intelligence → Supervisor → Agent

## Tech Stack (Updated - July 18, 2025)
- **Framework**: LangGraph 0.5.3+ with LangChain 0.3.8+
- **Patterns**: Command objects, create_react_agent, InjectedState, add_messages reducer
- **API**: FastAPI with webhook endpoints
- **State Management**: LangGraph StateGraph with InMemorySaver + BaseStore
- **Database**: Supabase for message queue and conversation history
- **Cache**: Redis for message batching (optional)
- **Monitoring**: LangSmith tracing integration
- **Deployment**: LangGraph Platform (LangSmith)
- **Python**: 3.11+ (required by LangGraph Platform)

## Modernization Implementation (2025-07-18)

### 1. Command Pattern for Agent Handoffs
```python
# OLD: Simple state updates
return {"next_agent": "sofia"}

# NEW: Command objects with explicit routing
@tool
def transfer_to_sofia(
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    return Command(
        goto="sofia",
        update={"messages": state["messages"] + [tool_message]},
        graph=Command.PARENT,
    )
```

### 2. create_react_agent Pattern
```python
# OLD: Custom agent classes
class SofiaAgent:
    def __init__(self):
        self.llm = ChatOpenAI().bind_tools(tools)
    async def process(self, state):
        # Custom processing logic

# NEW: Prebuilt pattern
agent = create_react_agent(
    model="openai:gpt-4",
    tools=appointment_tools_v2,
    state_schema=SofiaState,
    prompt=sofia_prompt,
    name="sofia"
)
```

### 3. Enhanced State Management
```python
# Custom state for each agent extending AgentState
class SofiaState(AgentState):
    contact_id: str
    contact_name: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    should_continue: bool = True

# Dynamic prompts based on state
def sofia_prompt(state: SofiaState) -> list[AnyMessage]:
    # Build context-aware system prompt
    contact_name = state.get("contact_name", "there")
    # ... customize based on state
```

### 4. Tool Injection Patterns
```python
# Tools now receive injected state and IDs
@tool
async def update_contact_with_state(
    contact_id: str,
    updates: Dict[str, Any],
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    # Full state access + return Commands
```

### 5. Memory Store Integration
```python
# Semantic search and persistence
@tool
def save_conversation_context(
    content: str,
    context_type: Literal["preference", "business_info", "goal"],
    *,
    store: Annotated[BaseStore, InjectedStore],
    state: Annotated[ConversationState, InjectedState]
) -> str:
    # Save to memory store with semantic search
```

### 6. Supervisor Pattern
```python
# Central routing supervisor
supervisor_agent = create_react_agent(
    model="openai:gpt-4",
    tools=[transfer_to_sofia, transfer_to_carlos, transfer_to_maria],
    prompt=supervisor_prompt,
    name="supervisor"
)

# Workflow starts with supervisor
workflow.set_entry_point("supervisor")
```

## File Structure (Current - Post Cleanup)
```
app/
├── agents/
│   ├── __init__.py            # v2 exports only
│   ├── sofia_agent_v2.py      # Modernized Sofia with Commands
│   ├── carlos_agent_v2.py     # Modernized Carlos with Commands
│   ├── maria_agent_v2.py      # Modernized Maria with Commands
│   └── supervisor.py          # Supervisor pattern orchestration
├── intelligence/
│   ├── analyzer.py            # Deterministic scoring & extraction
│   └── ghl_updater.py         # Persists scores to GHL
├── tools/
│   ├── agent_tools_v2.py      # Modernized tools with Commands
│   ├── webhook_enricher.py    # Loads full context from GHL
│   ├── conversation_loader.py # Loads conversation history
│   ├── ghl_client.py          # GHL API client
│   └── supabase_client.py     # Supabase client
├── utils/
│   ├── message_batcher.py     # 15-second batching for human-like responses
│   ├── message_utils.py       # Message trimming utilities
│   ├── simple_logger.py       # Logging utility
│   └── tracing.py             # LangSmith integration
├── state/
│   └── conversation_state.py  # State with add_messages reducer
├── api/
│   └── webhook.py             # FastAPI webhook endpoints
├── workflow.py                # Main entry (imports from v2)
├── workflow_v2.py             # Modernized workflow implementation
└── config.py                  # Configuration management
```

## Deployment History & Issues Fixed

### Phase 1: Initial Deployment Attempts
1. **Render Deployment Failed**:
   - Missing `pydantic-settings` dependency
   - Config expected .env file in production
   - Wrong gunicorn app reference

2. **Railway Deployment Failed**:
   - Same dependency issues as Render
   - Railway cached old "simple app" deployment
   - Could not update to new code

### Phase 2: LangGraph Platform Deployment
Fixed issues in order:

#### 1. Missing Dependencies
```python
pydantic-settings>=2.0.0
langgraph-sdk>=0.1.66
langgraph-checkpoint>=2.0.23
```

#### 2. Package Name Reserved Error
```bash
# Error: Package name 'src' is reserved
mv src app  # Renamed directory
# Updated all imports from "from src." to "from app."
```

#### 3. Dependency Conflicts
```python
# Error: postgrest==0.13.0 depends on httpx>=0.24.0,<0.25.0
supabase>=2.7.0  # Was 2.4.0
postgrest>=0.16.0  # Was 0.13.0
gotrue>=2.4.0
realtime>=2.0.0
```

#### 4. Import Errors
```python
# Error: attempted relative import with no known parent package
# Changed all relative to absolute imports
from app.state.conversation_state import ConversationState
from app.agents import sofia_node
```

### Phase 3: Modernization (Current)
Successfully implemented:
- Command pattern for routing
- create_react_agent for all agents
- Supervisor orchestration
- Memory store integration
- Enhanced state management
- Tool injection patterns

## Current Deployment Configuration

### LangGraph Platform Settings
- **Repository**: palinopr/ghl-langgraph-agent
- **Branch**: main
- **Config Path**: langgraph.json
- **Auto-deploy**: Enabled on push
- **Version**: v2 (modernized)

### Environment Variables
```bash
OPENAI_API_KEY=sk-proj-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
GHL_API_TOKEN=pit-...
GHL_LOCATION_ID=xxx
GHL_CALENDAR_ID=xxx
GHL_ASSIGNED_USER_ID=xxx
```

### Dependencies (Latest)
```python
# Core LangGraph
langgraph>=0.3.27
langchain>=0.3.8
langgraph-sdk>=0.1.66
langgraph-checkpoint>=2.0.23
langchain-core>=0.2.38
langsmith>=0.1.63

# Supabase (updated for compatibility)
supabase>=2.7.0
postgrest>=0.16.0
gotrue>=2.4.0
realtime>=2.0.0

# Performance
orjson>=3.9.7,<3.10.17
uvloop>=0.18.0
httptools>=0.5.0
structlog>=24.1.0
```

## Workflow Details (v2)

### Message Flow
1. Webhook receives GHL message at `/webhook/message`
2. **Supervisor** analyzes intent and routes via transfer tools
3. Selected agent processes with state-aware tools
4. Agents can handoff using Command objects
5. Response sent back through GHL API
6. State persisted with memory store

### Routing Logic (Supervisor-based)
- Supervisor uses transfer tools for explicit routing
- Each agent has handoff capabilities
- Dynamic routing based on conversation context
- Commands handle state updates and navigation

### State Management
- Extended AgentState for each agent
- InMemorySaver for conversation persistence
- BaseStore for semantic search
- Command objects for state updates
- Dynamic prompts based on state

## Testing the Modernized Implementation

```python
# Test individual agents
from app.agents.sofia_agent_v2 import sofia_agent
result = await sofia_agent.ainvoke({
    "messages": [{"role": "user", "content": "I need an appointment"}],
    "contact_id": "test123"
})

# Test supervisor routing
from app.agents.supervisor import create_supervisor_agent
supervisor = create_supervisor_agent()
result = await supervisor.ainvoke({
    "messages": [{"role": "user", "content": "I have a question"}]
})

# Test full workflow
from app.workflow_v2 import run_workflow_v2
result = await run_workflow_v2(
    contact_id="test123",
    message="I want to schedule a consultation",
    context={"name": "John Doe", "business": "E-commerce"}
)
```

## Common Patterns & Best Practices

### 1. Tool with State Injection
```python
@tool
def my_tool(
    param: str,
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    # Access state, return Command
```

### 2. Agent Creation
```python
agent = create_react_agent(
    model="openai:gpt-4",
    tools=tools_list,
    state_schema=CustomState,
    prompt=dynamic_prompt_function
)
```

### 3. Handoff Pattern
```python
def create_handoff_tool(agent_name: str):
    @tool
    def handoff_tool(...) -> Command:
        return Command(
            goto=agent_name,
            update={...},
            graph=Command.PARENT
        )
    return handoff_tool
```

## Deployment Status
- **Current Version**: v2 (modernized)
- **Status**: ✅ Successfully deployed
- **Platform**: LangGraph Platform (LangSmith)
- **Latest Commit**: 5e46c8d (Modernization complete)

## Future Enhancements
1. **Persistent Checkpointing**: Upgrade from InMemorySaver
2. **Advanced Memory**: Vector embeddings for better search
3. **Multi-modal**: Support for images/documents
4. **Analytics**: Agent performance tracking
5. **A/B Testing**: Prompt optimization

## Troubleshooting Guide

### Import Errors
- Ensure all imports are absolute (from app.xxx)
- Check Python version is 3.11+
- Verify langgraph dependencies

### Routing Issues
- Check supervisor tools are properly defined
- Verify Command objects have correct goto values
- Ensure graph has proper edges

### Memory Store
- Initialize with InMemoryStore() or persistent option
- Tools must use InjectedStore annotation
- Check store.search() query format

## Key Learnings
1. **Use Latest Patterns**: Command objects, create_react_agent
2. **State Injection**: Better than passing state manually
3. **Supervisor Pattern**: Cleaner than conditional edges
4. **Memory Integration**: Essential for context awareness
5. **Type Safety**: Use TypedDict and annotations

## Resources
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [Command Pattern](https://langchain-ai.github.io/langgraph/concepts/low_level/#command)
- [create_react_agent](https://langchain-ai.github.io/langgraph/reference/prebuilt/#create_react_agent)
- [Memory Store](https://langchain-ai.github.io/langgraph/concepts/persistence/#store)
- [Supervisor Pattern](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)

## Recent Enhancements (July 18, 2025 - v2)

### New Features Added
- **Streaming Responses**: Real-time token streaming for Sofia's appointment confirmations
- **Parallel Qualification**: Carlos can now check multiple criteria simultaneously (3x faster)
- **Context Window Management**: Automatic message trimming with `trim_messages`
- **Error Recovery**: Robust retry logic with circuit breakers and fallback responses
- **Performance Metrics**: Built-in monitoring for response times and token usage

### Enhanced Files
- `app/agents/sofia_agent_v2_enhanced.py` - Streaming appointment confirmations
- `app/agents/carlos_agent_v2_enhanced.py` - Parallel qualification checks
- `app/utils/error_recovery.py` - Comprehensive error handling utilities
- `app/workflow_enhanced.py` - Enhanced workflow with all new features
- `ENHANCEMENT_GUIDE.md` - Complete usage guide for new features

## Recent Cleanup (July 18, 2025)

### Removed Files
- **Old v1 Agents**: sofia_agent.py, carlos_agent.py, maria_agent.py, orchestrator.py
- **Old Tools**: agent_tools.py (v1 implementation)
- **Test Scripts**: test_setup.py, test_imports.py, simple_test.py, etc.
- **Deployment Scripts**: deploy-render.sh, setup-render-auth.sh, etc.
- **Old Configs**: render.yaml, vercel.json, railway-debug.toml
- **Unused Files**: main.py, worker.py, logger.py

### What Remains
- Only v2 implementations using modern patterns
- Intelligence layer for deterministic scoring
- Clean, focused codebase ready for production
- Essential deployment configs for LangGraph Platform

## Context Engineering Summary

### What This Project Does
This is a sophisticated multi-agent LangGraph system for GoHighLevel that:
1. **Intelligently routes leads** based on deterministic scoring (1-10 scale)
2. **Extracts Spanish patterns** using regex before LLM processing
3. **Persists all data to GHL** custom fields for continuity
4. **Batches messages** for human-like responses (15-second window)
5. **Loads full context** on every webhook for stateless operation

### Key Architecture Decisions
1. **Hybrid Intelligence**: Deterministic rules + LLM flexibility
2. **Stateless Design**: GHL is source of truth, survives restarts
3. **Human-Like Behavior**: Message batching prevents bot spam
4. **Full Observability**: LangSmith tracing for debugging
5. **Modern Patterns**: Command objects, create_react_agent, supervisor

### Critical Files
- `app/intelligence/analyzer.py` - Lead scoring and extraction
- `app/intelligence/ghl_updater.py` - Persists scores to GHL
- `app/utils/message_batcher.py` - Human-like response timing
- `app/tools/webhook_enricher.py` - Loads full context
- `app/workflow_v2.py` - Main orchestration flow

### Recent Enhancements (July 18, 2025)
1. **Intelligence Layer**: Pre-processes messages with Spanish extraction
2. **Score Persistence**: Saves to GHL custom fields automatically
3. **Message Batching**: Waits for complete thoughts before responding
4. **Context Loading**: Every message has full conversation history
5. **LangSmith Integration**: Complete tracing and debugging

### Testing Quick Start
```bash
# Send rapid messages to test batching
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi", "contactId": "test123"}'

curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"message": "My name is Jaime", "contactId": "test123"}'

curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{"message": "I have a restaurant", "contactId": "test123"}'

# Check score persistence in GHL custom fields
```

### Environment Setup
```bash
# Required
OPENAI_API_KEY=sk-...
GHL_API_TOKEN=pit-...
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...

# Recommended
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ghl-langgraph-agent

# Optional
REDIS_URL=redis://localhost:6379/0  # For distributed message batching
```

### Using Enhanced Features

#### Option 1: Quick Streaming Test
```python
# Stream Sofia's responses
from app.agents.sofia_agent_v2_enhanced import stream_appointment_confirmation

async for token in stream_appointment_confirmation(
    contact_id="test123",
    appointment_details={"date": "Tomorrow", "time": "2 PM"}
):
    print(token, end="", flush=True)
```

#### Option 2: Parallel Qualification
```python
# Quick lead scoring with Carlos
from app.agents.carlos_agent_v2_enhanced import quick_qualify_lead

result = await quick_qualify_lead(
    contact_id="test123",
    business_type="restaurant",
    budget="$500/month",
    goals="increase sales"
)
print(f"Lead Score: {result['total_score']}/10")
```

### Quick Development Setup
```bash
# Clone and setup
git clone https://github.com/palinopr/ghl-langgraph-agent.git
cd ghl-langgraph-agent
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Run locally
python app.py  # Starts on port 8000
```

## Intelligence Layer Implementation (v3)

### Overview
Inspired by n8n workflow analysis, we added a deterministic intelligence layer that runs BEFORE the AI agents. This combines the precision of rule-based extraction with the flexibility of LLM agents.

### Components

#### 1. SpanishPatternExtractor
```python
# Extracts structured data using regex patterns
- Names: "mi nombre es", "me llamo", "soy"
- Business: "tengo un/una", "mi negocio", "trabajo en"
- Budget: "como unos $300", "aproximadamente", "al mes"
- Goals: "necesito", "quiero", "busco"
```

#### 2. LeadScorer
```python
# Deterministic scoring (1-10 scale)
- Name only: 2-3 points
- Name + Business: 3-4 points
- Name + Business + Goal: 4-5 points
- Name + Business + Budget: 6-7 points
- Full info + clear intent: 8-10 points
- Never decreases score (persistence rule)
```

#### 3. BudgetConfirmationDetector
```python
# Contextual confirmation detection
- Detects "si/sí/yes/claro" after budget mention
- Boosts score to 6+ when $300+ confirmed
- Handles approximate amounts in Spanish
```

### Workflow Integration
```python
# New flow with intelligence layer
START → intelligence_node → supervisor → [sofia/carlos/maria] → supervisor → END

# Intelligence enriches state with:
- lead_score: 1-10 deterministic score
- extracted_data: Structured extraction
- score_history: Track changes over time
- suggested_agent: Routing recommendation
- score_reasoning: Explanation
```

### Benefits Over Pure LLM Approach
1. **Predictable Scoring**: Same input = same score
2. **Explainable**: Can trace why score was given
3. **Fast**: Regex extraction before LLM processing
4. **Debuggable**: Clear rules and patterns
5. **A/B Testable**: Can compare rule vs LLM performance

### Usage Example
```python
# State after intelligence analysis
{
    "lead_score": 6,
    "lead_category": "warm",
    "suggested_agent": "carlos",
    "extracted_data": {
        "name": "Jaime",
        "business_type": "restaurante",
        "budget": "300+",
        "goal": "automatizar marketing"
    },
    "score_reasoning": "Score 6: has name, has business (restaurante), has substantial budget (300+)"
}
```

## Latest Updates (July 18, 2025)

### 1. Message Batching for Human-Like Responses
- **Problem**: Bot responds to each message individually
- **Solution**: 15-second batch window to collect messages
- **Result**: Natural conversation flow
- **File**: `app/utils/message_batcher.py`

### 2. Full Context Loading
- **Problem**: Each message processed without history
- **Solution**: Load complete conversation from GHL on every webhook
- **Result**: Perfect context continuity
- **Files**: `app/tools/webhook_enricher.py`, `app/tools/conversation_loader.py`

### 3. Automatic Score Updates
- **Problem**: Scores only in memory, lost on restart
- **Solution**: Save scores to GHL custom fields after analysis
- **Result**: Persistent lead progress
- **File**: `app/intelligence/ghl_updater.py`

### 4. LangSmith Tracing
- **Problem**: No visibility into agent decisions
- **Solution**: Complete tracing integration
- **Result**: Full observability and debugging
- **File**: `app/utils/tracing.py`

### 5. Message Trimming
- **Problem**: Token limits with long conversations
- **Solution**: Intelligent message trimming
- **Result**: Handles conversations of any length
- **File**: `app/utils/message_utils.py`

## Complete Process Flow

### 1. Message Reception
```
Webhook → Message Batcher → Wait for more messages (15s window)
```

### 2. Context Loading
```
WebhookEnricher:
- Loads contact details from GHL
- Loads custom fields (including previous score)
- Loads conversation history (50 messages)
- Prepares enriched initial state
```

### 3. Intelligence Analysis
```
IntelligenceAnalyzer:
- Extracts Spanish patterns (regex-based)
- Calculates lead score (deterministic)
- Detects budget confirmations
- Never decreases score
```

### 4. GHL Updates
```
GHLUpdater:
- Updates lead score → Custom field
- Updates all extracted data → Custom fields
- Adds tags based on score/category
- Ensures persistence
```

### 5. Routing
```
Supervisor:
- Reads enriched state with score
- Routes based on score + context
- Transfers control via Commands
```

## Key Design Decisions

### 1. Stateless Architecture
- Every message loads full context
- No in-memory state between messages
- Survives restarts, scales horizontally

### 2. GHL as Source of Truth
- All data persisted in GHL
- Custom fields store state
- Tags provide quick filtering

### 3. Deterministic + AI Hybrid
- Regex extraction for reliability
- AI for complex understanding
- Best of both worlds

### 4. Human-Like Behavior
- Message batching prevents spam
- Natural response timing
- Context-aware responses

## Critical File Paths & Responsibilities

### Core Workflow
- `app/workflow_v2.py` - Main orchestration
- `app/state/conversation_state.py` - State schema with add_messages

### Intelligence Layer
- `app/intelligence/analyzer.py` - Score calculation & extraction
- `app/intelligence/ghl_updater.py` - Saves scores to GHL

### Context Loading
- `app/tools/webhook_enricher.py` - Enriches webhook data
- `app/tools/conversation_loader.py` - Loads conversation history

### Human-Like Features
- `app/utils/message_batcher.py` - Message batching logic
- `app/utils/message_utils.py` - Message trimming

### Monitoring
- `app/utils/tracing.py` - LangSmith integration
- `app/__init__.py` - Auto-setup tracing

## Custom Field Mappings (GHL)
```python
FIELD_MAPPINGS = {
    "score": "wAPjuqxtfgKLCJqahjo1",        # Lead score (1-10)
    "intent": "Q1n5kaciimUU6JN5PBD6",       # EXPLORANDO/EVALUANDO/LISTO_COMPRAR
    "business_type": "HtoheVc48qvAfvRUKhfG", # Business type
    "urgency_level": "dXasgCZFgqd62psjw7nd", # ALTA/NO_EXPRESADO
    "goal": "r7jFiJBYHiEllsGn7jZC",         # Customer goal
    "budget": "4Qe8P25JRLW0IcZc5iOs",       # Budget amount
    "name": "TjB0I5iNfVwx3zyxZ9sW",         # Verified name
    "preferred_day": "D1aD9KUDNm5Lp4Kz8yAD", # Appointment day
    "preferred_time": "M70lUtadchW4f2pJGDJ5" # Appointment time
}
```

## Environment Variables
```bash
# Required
OPENAI_API_KEY=sk-...
GHL_API_TOKEN=pit-...
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...

# LangSmith (Recommended)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ghl-langgraph-agent

# Optional
REDIS_URL=redis://localhost:6379/0
```

## Testing Checklist
- [ ] Message batching works (send 3 quick messages)
- [ ] Score persists in GHL (check custom fields)
- [ ] Tags update correctly (hot-lead, warm-lead, etc.)
- [ ] Conversation history loads (check logs)
- [ ] LangSmith shows traces
- [ ] Spanish extraction works
- [ ] Budget detection triggers score bump

## Common Issues & Solutions

### Issue: Score not updating
- Check GHL API token has write permissions
- Verify custom field IDs match
- Check logs for GHL update errors

### Issue: Messages processed individually
- Ensure Redis is running (or fallback works)
- Check batch window timing
- Verify webhook processing

### Issue: No conversation history
- Check GHL API permissions
- Verify contact ID is correct
- Check conversation history endpoint

## Context for Future Development
When working on this project:
1. Always use v2 patterns (Command, create_react_agent)
2. Extend from AgentState for custom states
3. Use tool injection (InjectedState, InjectedToolCallId)
4. Implement handoffs via Command objects
5. Leverage memory store for context
6. Test with Context7 MCP for latest docs
7. Consider intelligence layer for structured extraction before LLM processing
8. Use deterministic scoring for predictable lead qualification
9. Ensure all state changes are persisted to GHL
10. Test with rapid message sequences for human-like behavior