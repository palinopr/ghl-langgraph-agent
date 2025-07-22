# ARCHITECTURE.md

## 🏗️ System Architecture

The LangGraph GHL Agent is a sophisticated multi-agent system built on LangGraph v0.5.3+ that handles WhatsApp/SMS conversations for GoHighLevel.

## High-Level Overview

```
WhatsApp/SMS → GHL → Webhook → Workflow → Agent → Response → GHL → WhatsApp/SMS
                                    ↓
                              Intelligence Layer
                                    ↓
                               Supervisor
                              ↙    ↓    ↘
                         Maria  Carlos  Sofia
```

## Core Components

### 1. Workflow Engine (`app/workflow.py`)

The main orchestration layer using LangGraph StateGraph:

- **Entry**: Webhook receives message
- **Receptionist**: Loads context from GHL
- **Intelligence**: Analyzes and scores lead (1-10)
- **Supervisor**: Routes based on score
- **Agents**: Process conversation
- **Responder**: Sends response back

### 2. State Management (`app/state/minimal_state.py`)

Simplified state with only essential fields:

```python
class MinimalState(TypedDict):
    # Core fields
    messages: Annotated[List[BaseMessage], add_messages]
    contact_id: str
    thread_id: Optional[str]
    webhook_data: Dict[str, Any]
    
    # Lead intelligence
    lead_score: int  # 1-10
    lead_category: Literal["cold", "warm", "hot"]
    extracted_data: Dict[str, Any]
    
    # Agent routing
    current_agent: Literal["maria", "carlos", "sofia"]
    next_agent: Optional[str]
    agent_task: Optional[str]
    
    # Control flags
    should_end: bool
    needs_rerouting: bool
    needs_escalation: bool
```

### 3. Intelligence Layer (`app/intelligence/analyzer.py`)

Deterministic lead analysis and scoring:

- **Spanish Pattern Extraction**: Names, business types, budgets
- **Lead Scoring**: 1-10 scale based on data completeness
- **Budget Detection**: Identifies confirmed budgets
- **Typo Tolerance**: Handles common misspellings

Score calculation:
- Name only: 2-3 points
- Name + Business: 3-4 points  
- Name + Business + Goal: 4-5 points
- Name + Business + Budget: 6-7 points
- Full info + clear intent: 8-10 points

### 4. Agent System

#### Base Agent (`app/agents/base_agent.py`)
Common utilities for all agents:
- Message extraction
- Score boundary checking
- Error handling
- Data status checking

#### Maria - Cold Leads (Score 0-4)
- Initial contact and trust building
- Basic information gathering
- Friendly, welcoming personality
- Escalates when score reaches 5

#### Carlos - Warm Leads (Score 5-7)
- Qualification specialist
- WhatsApp automation benefits
- Value proposition
- Escalates when score reaches 8

#### Sofia - Hot Leads (Score 8-10)
- Appointment booking
- Calendar integration
- Confirmation handling
- Strict data collection order

### 5. Supervisor (`app/agents/supervisor_official.py`)

Central orchestrator using `create_react_agent`:
- Analyzes conversation context
- Routes to appropriate agent
- Handles escalations
- Provides task descriptions

Key features:
- Deterministic routing based on score
- Command objects for agent handoffs
- InjectedToolCallId for proper tool handling
- No direct agent-to-agent transfers (prevents loops)

### 6. Tools (`app/tools/`)

#### GHL Client (`ghl_client_simple.py`)
Simplified API client with only used methods:
- Contact management
- Message sending
- Conversation history
- Calendar operations
- Custom field updates

#### Agent Tools (`agent_tools_modernized.py`)
- `get_contact_details_with_task`
- `update_contact_with_context`
- `escalate_to_supervisor`
- `book_appointment_with_instructions`

### 7. Message Flow

1. **Webhook Reception** (`app/api/webhook.py`)
   - Receives GHL webhook
   - Basic validation
   - Queues for processing

2. **Context Loading** (`app/tools/webhook_enricher.py`)
   - Loads contact details
   - Fetches conversation history
   - Gets custom fields
   - Prepares initial state

3. **Intelligence Analysis**
   - Extracts Spanish patterns
   - Calculates lead score
   - Never decreases score
   - Updates GHL custom fields

4. **Routing Decision**
   - Score 0-4 → Maria
   - Score 5-7 → Carlos
   - Score 8-10 → Sofia
   - Escalations → Back to supervisor

5. **Agent Processing**
   - Agent receives enriched context
   - Processes with LLM
   - May use tools
   - Returns response

6. **Response Handling**
   - Human-like delays
   - Message batching
   - GHL API update
   - Confirmation tracking

## Design Principles

### 1. Stateless Architecture
- Every webhook loads full context
- No in-memory state between messages
- GHL is the source of truth
- Survives restarts

### 2. Deterministic Intelligence
- Regex-based extraction (not LLM)
- Predictable scoring
- Consistent behavior
- Fast and reliable

### 3. Linear Flow
- No agent-to-agent transfers
- Always through supervisor
- Prevents circular loops
- Clear escalation path

### 4. Human-Like Behavior
- Natural typing delays
- Message batching
- Conversation timing
- Authentic feel

### 5. Fault Tolerance
- Graceful error handling
- Automatic retries
- Rate limit handling
- Fallback responses

## Performance Optimizations

### Python 3.13 Features
- **GIL-free mode**: True parallelism
- **JIT compilation**: Hot path optimization
- **TaskGroup**: Concurrent operations

### Simplified State
- Reduced from 113 to 23 fields
- 79.6% field reduction
- Faster serialization
- Less memory usage

### Efficient Patterns
- Shared base agent utilities
- Generic GHL API caller
- Consolidated error handling
- Minimal dependencies

## Integration Points

### GoHighLevel
- Webhook endpoint: `/webhook/message`
- Custom fields for persistence
- Contact tags for categorization
- Calendar for appointments

### LangSmith
- Full trace visibility
- Error tracking
- Performance monitoring
- Debug capabilities

### External Services
- OpenAI for LLM
- Supabase for message batching (optional)
- Redis for distributed cache (optional)

## Security Considerations

1. **API Key Management**: Environment variables only
2. **Webhook Validation**: Verify GHL source
3. **Data Privacy**: No PII in logs
4. **Rate Limiting**: Respect API limits
5. **Error Messages**: No sensitive data exposed

## Scaling Architecture

- **Horizontal**: Each webhook independent
- **Vertical**: Python 3.13 optimizations
- **Caching**: Redis for shared state
- **Batching**: Message aggregation
- **Rate Limits**: Exponential backoff

## Monitoring & Observability

1. **Health Endpoints**
   - `/health` - Basic health
   - `/metrics` - Performance stats
   - `/ok` - Simple alive check

2. **LangSmith Tracing**
   - Every workflow execution
   - Tool invocations
   - Error details
   - Performance metrics

3. **Custom Logging**
   - Structured logs
   - Contextual information
   - Error tracking
   - Debug levels

## Future Architecture Considerations

1. **Vector Store**: For semantic search
2. **Streaming**: Real-time responses
3. **Multi-modal**: Image/document support
4. **Federation**: Multi-location support
5. **Analytics**: Business intelligence