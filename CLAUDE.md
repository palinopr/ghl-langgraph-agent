# Claude Context: LangGraph GHL Agent - Complete Implementation Guide

## Project Overview
This is a LangGraph-based GoHighLevel (GHL) messaging agent that handles intelligent lead routing and appointment booking. The system uses three AI agents (Maria, Carlos, Sofia) orchestrated by a supervisor using the latest LangGraph patterns.

## Architecture Evolution

### Original Architecture (v1)
- **Maria** (Cold Leads, Score 1-4): Customer support, initial contact
- **Carlos** (Warm Leads, Score 5-7): Lead qualification specialist
- **Sofia** (Hot Leads, Score 8-10): Appointment booking specialist
- **Orchestrator**: Routes messages to appropriate agents based on intent

### Modernized Architecture (v2) - CURRENT
- **Supervisor**: Central orchestrator using `create_react_agent` pattern
- **Maria**: Support agent with handoff capabilities via Command objects
- **Carlos**: Qualification agent with state-aware tools
- **Sofia**: Appointment agent with direct booking and memory integration
- **Memory Store**: Semantic search and conversation persistence

## Tech Stack (Updated)
- **Framework**: LangGraph 0.3.27+ with LangChain 0.3.8+
- **Patterns**: Command objects, create_react_agent, InjectedState
- **API**: FastAPI with webhook endpoints
- **State Management**: LangGraph StateGraph with InMemorySaver + BaseStore
- **Database**: Supabase for message queue and conversation history
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

## File Structure (Current)
```
app/
├── agents/
│   ├── __init__.py            # Original exports
│   ├── sofia_agent.py         # Original Sofia (v1)
│   ├── sofia_agent_v2.py      # Modernized Sofia
│   ├── carlos_agent.py        # Original Carlos (v1)
│   ├── carlos_agent_v2.py     # Modernized Carlos
│   ├── maria_agent.py         # Original Maria (v1)
│   ├── maria_agent_v2.py      # Modernized Maria
│   ├── orchestrator.py        # Original orchestrator
│   └── supervisor.py          # New supervisor pattern
├── tools/
│   ├── agent_tools.py         # Original tools
│   └── agent_tools_v2.py      # Modernized tools with Commands
├── state/
│   └── conversation_state.py  # State definitions
├── workflow.py               # Main workflow (now uses v2)
└── workflow_v2.py           # Modernized workflow implementation
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

## Context for Future Development
When working on this project:
1. Always use v2 patterns (Command, create_react_agent)
2. Extend from AgentState for custom states
3. Use tool injection (InjectedState, InjectedToolCallId)
4. Implement handoffs via Command objects
5. Leverage memory store for context
6. Test with Context7 MCP for latest docs