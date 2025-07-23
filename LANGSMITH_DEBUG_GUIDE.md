# Comprehensive LangSmith Debug Integration Guide

## Overview
We've implemented comprehensive debugging that captures EVERYTHING in your LangSmith traces. Every agent decision, tool call, state change, message flow, and API interaction is now logged.

## What's Captured

### 1. **Node Execution** (Automatic)
Every node (agent) automatically logs:
- **Entry**: State keys, thread ID, contact ID, timestamp
- **State Snapshots**: Complete state before and after execution
- **Changes**: What the node modified
- **Exit**: Success/failure status
- **Errors**: Full error details if something fails

### 2. **Tool Executions** (Automatic)
Every tool call logs:
- Tool name and inputs
- Execution start time
- Success/failure status
- Output (truncated if large)
- Error details if failed

### 3. **Agent-Specific Logging**

#### Thread Mapper
- Webhook data analysis
- Thread ID mapping decisions
- Pre-population detection

#### Receptionist
- GHL API calls (conversations, messages)
- Message loading results
- Message deduplication decisions

#### Smart Router
- Message analysis (score, intent, urgency, sentiment)
- Routing decisions with reasons
- Score changes with explanations
- Data extraction results

#### Agents (Maria, Carlos, Sofia)
- All inherit base debugging
- Tool usage patterns
- Decision making process

#### Responder
- Message preparation details
- Send success/failure
- Multi-part message handling

### 4. **Workflow Level**
- Workflow start with initial context
- Final results and metrics
- Total execution time

## Finding Information in LangSmith

### View Complete Execution Flow
1. Go to your LangSmith project
2. Find your trace by ID or timestamp
3. Click on the trace to expand

### Understanding the Trace Structure
```
Workflow Run
├── thread_id_mapper_debug
│   ├── webhook_analysis (metadata)
│   ├── state_snapshot_entry
│   └── state_snapshot_exit
├── receptionist_debug
│   ├── ghl_api_call (loading conversations)
│   ├── ghl_api_result (messages loaded)
│   ├── message_flow_analysis
│   └── state_snapshots
├── smart_router_debug
│   ├── routing_context
│   ├── message_analysis (score, intent, etc.)
│   ├── routing_decision
│   └── state_changes
├── maria_agent_debug (or carlos/sofia)
│   ├── tool calls (tracked individually)
│   └── state_snapshots
└── responder_debug
    ├── responder_preparation
    └── responder_success
```

### Key Metadata Fields to Look For

#### For Debugging Message Issues:
- Look for `message_flow_*` metadata
- Check `state_snapshot_*` for message counts
- Review `ghl_api_result` for loaded messages

#### For Routing Issues:
- Check `routing_context` and `routing_decision`
- Review `message_analysis` for scoring details
- Look at `score_history` in state

#### For Tool Failures:
- Find `tool_*` metadata entries
- Check for `tool_*_error` entries
- Review tool inputs and outputs

#### For API Issues:
- Look for `ghl_api_call` and `ghl_api_result`
- Check `ghl_api_error` for failures
- Review timing and response data

## Debug Mode Features

### 1. **State Validation**
Every node validates its input state and logs issues

### 2. **Message Flow Tracking**
Tracks message accumulation across nodes:
- Message type counts
- Last 5 messages for context
- Duplication detection

### 3. **Decision Tracking**
- Why agents made specific choices
- Score changes with reasons
- Routing decisions with context

### 4. **Error Context**
When errors occur, captures:
- Full error type and message
- State at time of error
- Recovery attempts

## Using Debug Information

### Finding Specific Issues

#### "Why didn't the agent respond?"
1. Check `routing_decision` - where was it routed?
2. Review `message_analysis` - what was detected?
3. Look at agent's `state_snapshot_exit` - what changed?
4. Check `responder_preparation` - was a message prepared?

#### "Why is the score not changing?"
1. Review `message_analysis` for each message
2. Check `routing_context` for previous scores
3. Look for `score_history` in state

#### "Why did a tool fail?"
1. Find the specific `tool_*` entry
2. Check inputs in `tool_*_start`
3. Review error in `tool_*_error`

### Performance Analysis
- Check timestamps in metadata
- Review API call durations
- Identify bottlenecks in execution

## Best Practices

1. **Use Trace IDs**: Always include the LangSmith trace ID when reporting issues
2. **Check Metadata**: Most debugging info is in the metadata tabs
3. **Follow Execution Order**: Traces show chronological execution
4. **Review State Changes**: Compare entry/exit states to understand changes
5. **Check Tool Calls**: Many issues stem from tool execution problems

## Example Debug Session

```
Problem: "Agent not responding to customer"

1. Open trace in LangSmith
2. Expand "smart_router_debug"
3. Check "routing_decision" metadata
   → Found: Routed to Maria with score 2
4. Expand "maria_agent_debug" 
5. Check "state_snapshot_exit"
   → Found: Message added to state
6. Expand "responder_debug"
7. Check "responder_preparation"
   → Found: No AI message found to send
8. Root cause: Maria didn't generate a response
```

## Advanced Debugging

### Custom Logging
Add your own debug points:
```python
from app.utils.langsmith_debug import log_to_langsmith

# Log custom metadata
log_to_langsmith({
    "custom_field": "value",
    "debug_info": "checking something"
}, "custom_debug_point")
```

### State Debugging
```python
from app.utils.langsmith_debug import debug_state

# Log state at any point
debug_state(state, "before_processing")
```

## Summary
With this comprehensive debugging integration, you can see EVERYTHING that happens in your workflow directly in LangSmith. No more guessing - every decision, API call, and state change is tracked and visible.