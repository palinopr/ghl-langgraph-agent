# DEVELOPMENT.md

## 🛠️ Development Guide

This guide covers local development setup, testing, and debugging for the LangGraph GHL Agent.

## Local Development Setup

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd langgraph-ghl-agent

# Create Python 3.13 virtual environment
python3.13 -m venv venv_langgraph
source venv_langgraph/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create `.env` file:
```bash
# Required for development
OPENAI_API_KEY=sk-proj-...
GHL_API_TOKEN=pit-...
GHL_LOCATION_ID=xxx
GHL_CALENDAR_ID=xxx
GHL_ASSIGNED_USER_ID=xxx

# LangSmith (highly recommended)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ghl-langgraph-agent

# Optional
LOG_LEVEL=DEBUG
```

### 3. Quick Validation

```bash
# Validate workflow (5 seconds)
make validate

# Run tests
make test

# Start development server
make run
```

## Testing Strategies

### 1. Production-Like Testing (Recommended)

```bash
# Run with real GHL data
python run_like_production.py

# Options:
# 1. Single message test
# 2. Full conversation flow
# 3. Custom contact test
```

### 2. Unit Testing

```bash
# Run specific test
pytest tests/test_agents.py::test_maria_routing -v

# Run with coverage
pytest --cov=app tests/
```

### 3. Integration Testing

```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "contactId": "test123",
    "message": "Hola, tengo un restaurante"
  }'

# Test health endpoint
curl http://localhost:8000/health
```

## Debugging Techniques

### 1. LangSmith Traces

```python
# Enable detailed tracing
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "ghl-debug"

# View traces at https://smith.langchain.com
```

### 2. Local Trace Analysis

```bash
# Fetch specific trace
python fetch_trace_curl.py <trace_id>

# Analyze recent errors
python analyze_trace.py --errors-only

# Debug specific contact
python debug_contact.py <contact_id>
```

### 3. Workflow Debugging

```python
# Add debug logging
from app.utils.simple_logger import get_logger
logger = get_logger("debug")
logger.debug(f"State: {state}")

# Enable verbose mode
LOG_LEVEL=DEBUG python app.py
```

### 4. Common Debug Scenarios

#### Debug Agent Routing
```python
# Check lead score
print(f"Lead score: {state['lead_score']}")
print(f"Current agent: {state['current_agent']}")
print(f"Should route to: {get_agent_for_score(score)}")
```

#### Debug Message Extraction
```python
# Test pattern extraction
from app.intelligence.analyzer import IntelligenceAnalyzer
analyzer = IntelligenceAnalyzer()
result = analyzer.extract_spanish_patterns("Hola soy Maria")
print(result)
```

#### Debug Tool Execution
```python
# Test GHL client
from app.tools.ghl_client import ghl_client
contact = await ghl_client.get_contact("test_id")
print(contact)
```

## Development Workflow

### 1. Making Changes

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes
# ... edit files ...

# Validate changes
make validate

# Test locally
python run_like_production.py
```

### 2. Testing Changes

```bash
# Run unit tests
pytest tests/

# Test specific scenario
python test_scenario.py

# Check with real data
python run_like_production.py
```

### 3. Pre-Commit Checks

```bash
# Format code
black app/

# Check types
mypy app/

# Run linter
flake8 app/

# Validate workflow
make validate
```

## Common Development Tasks

### 1. Adding a New Tool

```python
# In app/tools/your_tool.py
from langgraph.prebuilt import tool

@tool
def your_new_tool(param: str) -> str:
    """Tool description"""
    # Implementation
    return result

# Add to agent tools
tools = [existing_tools..., your_new_tool]
```

### 2. Modifying Agent Behavior

```python
# In app/agents/agent_name.py
def agent_prompt(state):
    # Modify prompt logic
    return updated_prompt

# Test thoroughly
python test_agent_changes.py
```

### 3. Adding State Fields

```python
# In app/state/minimal_state.py
class MinimalState(TypedDict):
    # Existing fields...
    new_field: Optional[str]  # Add with Optional for compatibility
```

### 4. Updating Intelligence Layer

```python
# In app/intelligence/analyzer.py
# Add new patterns
NEW_PATTERNS = {
    "your_pattern": re.compile(r"..."),
}
```

## Performance Profiling

### 1. Profile Workflow

```bash
# Run with profiling
python -m cProfile -o profile.stats app.py

# Analyze results
python -m pstats profile.stats
```

### 2. Monitor Memory

```python
import tracemalloc
tracemalloc.start()

# Your code here

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 10**6:.1f} MB")
```

### 3. Benchmark Operations

```python
import time

start = time.time()
# Operation to benchmark
elapsed = time.time() - start
print(f"Operation took: {elapsed:.3f}s")
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure virtual environment is activated
   source venv_langgraph/bin/activate
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

2. **Workflow Validation Fails**
   ```bash
   # Check for circular imports
   python -c "import app.workflow"
   # Run validation
   python validate_workflow.py
   ```

3. **GHL API Errors**
   ```python
   # Check credentials
   print(os.getenv("GHL_API_TOKEN"))
   # Test connection
   await ghl_client.verify_connection()
   ```

4. **Agent Not Responding**
   ```python
   # Check state
   print(f"Messages: {len(state['messages'])}")
   print(f"Current agent: {state['current_agent']}")
   # Enable debug logging
   ```

## Best Practices

### 1. Code Style
- Use type hints
- Follow PEP 8
- Add docstrings
- Keep functions small

### 2. Testing
- Write tests for new features
- Test edge cases
- Use real data when possible
- Validate before committing

### 3. State Management
- Keep state minimal
- Use Optional for new fields
- Document state changes
- Test state transitions

### 4. Error Handling
- Use try/except blocks
- Log errors with context
- Return graceful failures
- Never expose secrets

## Quick Reference

```bash
# Setup
source venv_langgraph/bin/activate

# Validate
make validate

# Test
python run_like_production.py

# Debug
LOG_LEVEL=DEBUG python app.py

# Profile
python -m cProfile app.py

# Deploy check
make test && make validate
```

## Useful Scripts

- `validate_workflow.py` - Quick validation
- `run_like_production.py` - Production-like testing
- `fetch_trace_curl.py` - Trace analysis
- `debug_contact.py` - Contact debugging
- `test_ghl_connection.py` - API testing

Remember: **Always test with real data before deploying!**