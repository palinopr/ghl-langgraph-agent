# LangSmith Tracing Setup Guide

## Overview
LangSmith tracing is now integrated into the GHL LangGraph Agent to provide visibility into:
- All LLM calls and costs
- Agent decision making
- Lead scoring and routing
- Performance metrics
- Error tracking

## Setup Instructions

### 1. Add Your LangSmith API Key
Add these environment variables to your `.env` file:

```bash
# LangSmith Configuration
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=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
LANGSMITH_PROJECT=ghl-langgraph-agent

# Legacy support (also add these)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=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
LANGCHAIN_PROJECT=ghl-langgraph-agent
```

### 2. Verify Setup
When you start the application, you should see:
```
✅ LangSmith tracing is enabled
```

### 3. What Gets Traced

#### Workflow Level
- Complete workflow execution
- Time taken for each step
- State transitions
- Agent handoffs

#### Intelligence Layer
- Spanish pattern extraction
- Lead scoring calculations
- Score reasoning
- Extraction confidence

#### Agent Level
- Each agent's reasoning
- Tool usage
- Response generation
- Handoff decisions

#### API Calls
- GHL API interactions
- Retry attempts
- Response times

### 4. Viewing Traces in LangSmith

1. Go to https://smith.langchain.com
2. Navigate to your project: `ghl-langgraph-agent`
3. You'll see:
   - **Traces**: Full conversation flows
   - **Runs**: Individual component executions
   - **Feedback**: Lead scores and quality metrics
   - **Metrics**: Cost, latency, token usage

### 5. Key Metrics to Monitor

#### Lead Quality
- Average lead scores over time
- Score distribution by agent
- Conversion rates (score improvements)

#### Performance
- Average response time
- Token usage per conversation
- Cost per lead

#### Errors
- Failed API calls
- Extraction failures
- Routing errors

### 6. Custom Feedback

The system automatically logs:
- **Lead Score**: After each intelligence analysis (0-10 normalized to 0-1)
- **Score Reasoning**: Why the score was assigned
- **Agent Performance**: Success/failure of agent actions

### 7. Debugging with LangSmith

When debugging issues:
1. Find the trace by contact_id or timestamp
2. Examine the full execution flow
3. Check state at each step
4. Review LLM prompts and responses
5. Identify bottlenecks or errors

### 8. Cost Optimization

Monitor in LangSmith:
- Token usage by agent
- Most expensive operations
- Opportunities for caching
- Message trimming effectiveness

## Integration Details

### Automatic Tracing
All LangChain/LangGraph operations are automatically traced:
```python
# No code changes needed - it just works!
agent = create_react_agent(...)  # Automatically traced
workflow.invoke(...)  # Automatically traced
```

### Manual Tracing
For custom operations:
```python
from app.utils.tracing import TracedOperation

async with TracedOperation(
    "custom_operation",
    metadata={"contact_id": "123"},
    tags=["custom", "operation"]
):
    # Your code here
    pass
```

### Logging Feedback
```python
from app.utils.tracing import log_feedback

log_feedback(
    run_id=run_id,
    score=0.8,
    feedback_type="agent_performance",
    comment="Successfully booked appointment"
)
```

## Benefits

1. **Complete Visibility**: See every step of lead processing
2. **Performance Monitoring**: Track latency and costs
3. **Quality Assurance**: Monitor lead scoring accuracy
4. **Debugging**: Quickly identify and fix issues
5. **Optimization**: Find opportunities to improve

## Troubleshooting

If tracing isn't working:
1. Check API key is correct
2. Verify internet connectivity
3. Check logs for connection errors
4. Ensure environment variables are loaded
5. Try running: `python -c "from app.utils.tracing import setup_langsmith_tracing; print(setup_langsmith_tracing())"`

## Privacy Note
- Only metadata is sent to LangSmith by default
- PII can be excluded via configuration
- All data is encrypted in transit
- Retention policies can be configured in LangSmith dashboard