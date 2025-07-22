# Local Development with LangGraph Platform

## Quick Start

```bash
# Install LangGraph CLI
pip install langgraph-cli

# Set environment to disable tracing by default
export LANGSMITH_TRACING=false

# Start dev server with auto-reload
make dev
# Or directly: langgraph dev --no-browser
```

The dev server:
- Runs on http://localhost:8123 (LangGraph Studio)
- Auto-reloads on code changes
- Provides interactive graph visualization
- Allows step-through debugging

## Repository Structure

```
langgraph-ghl-agent/
├── src/                 # LangGraph exports
│   ├── graph.py         # Exports workflow as 'graph'
│   └── webapp.py        # Exports FastAPI app
├── app/
│   ├── agents/          # Agent implementations
│   ├── api/             # FastAPI webhook handlers
│   ├── intelligence/    # Lead analysis and scoring
│   ├── state/           # LangGraph state definitions
│   ├── tools/           # GHL API clients
│   ├── utils/           # Helpers
│   └── workflow.py      # Main LangGraph workflow
├── tests/               # Test suite
├── langgraph.json       # LangGraph configuration
└── requirements.txt     # Python dependencies
```

## LangGraph State Persistence

The system supports two persistence backends:

### Local Development (SQLite)
- **Location**: `app/checkpoints.db`
- **Implementation**: `langgraph-checkpoint-sqlite` package
- **Thread Management**: Maps GHL conversation IDs to LangGraph thread IDs
- **Memory**: Maintains conversation history across webhook calls

### Production (Redis)
- **Backend**: Redis 7+
- **Implementation**: Custom `RedisCheckpointSaver` in `src/state/redis_store.py`
- **Configuration**: Set `REDIS_URL` environment variable
- **Features**:
  - Distributed deployment support
  - Automatic TTL (7 days default)
  - Atomic operations
  - Observability spans for state operations

To use Redis locally:
```bash
# Option 1: Use make dev (auto-starts Redis)
make dev

# Option 2: Manual Redis setup
docker run -d --name redis-local -p 6379:6379 redis:7-alpine
export REDIS_URL=redis://localhost:6379/0
langgraph dev --no-browser
```
- **Configuration**: Auto-configured in `workflow.py` with configurable memory saver

## Webhook to Graph Mapping

1. **Webhook Receipt** (`app/api/webhook_simple.py`):
   - GHL sends POST to `/webhooks/chat/inbound`
   - Extracts: contactId, conversationId, message, locationId

2. **Intelligence Layer** (`app/intelligence/analyzer.py`):
   - Extracts Spanish patterns (name, phone, email, business)
   - Scores lead 1-10 based on information completeness
   - Handles typos with fuzzy matching

3. **Graph Invocation** (`app/workflow.py`):
   - Creates/retrieves thread using conversation ID
   - Passes score to supervisor for agent routing
   - Streams responses back through GHL API

## Open TODOs & Pain Points

### 1. **Supabase Dependency** (Critical)
- Current code has optional Supabase integration
- Webhook handler falls back gracefully if unavailable
- Consider removing completely or documenting setup

### 2. **Test Coverage** 
- No comprehensive test suite exists
- Need unit tests for agents and intelligence layer
- Integration tests for webhook flow missing

### 3. **Environment Management**
- Multiple virtual environments in repo (venv, venv313, venv_langgraph)
- Should standardize on single approach
- Poetry would provide better dependency management

### 4. **Configuration Sprawl**
- Settings scattered across multiple .env files
- No centralized config management
- Missing validation for required env vars

### 5. **Error Recovery**
- Basic error handling exists but needs enhancement
- No retry logic for GHL API calls
- Missing circuit breaker pattern

### 6. **Performance Monitoring**
- LangSmith integration configured but not documented
- No metrics collection for response times
- Missing health check endpoint details

### 7. **Development Experience**
- Hot-reload works but requires manual container restart sometimes
- No pre-commit hooks for code quality
- Missing API documentation generation

## Development Workflow

1. **Local Testing**: Use `make dev` to start LangGraph Studio
2. **Unit Tests**: Run `pytest -q` for quick test validation
3. **Type Checking**: Run `mypy app/ src/` before committing
4. **Linting**: Run `ruff check .` to ensure code quality
5. **Graph Testing**: Run `langgraph test` to validate workflow

## Debugging Tips

- Use LangGraph Studio's step-through debugger
- Enable tracing: `export LANGSMITH_TRACING=true`
- Check logs in Studio's console output
- Inspect state at each node in the graph UI