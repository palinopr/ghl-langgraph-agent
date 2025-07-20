# Trace Collector Usage Guide

## What We Built

A real-time trace collection system that captures everything happening in your workflow, making debugging super easy!

## How It Works

1. **Automatic Collection**: Every webhook request is traced automatically
2. **Detailed Timeline**: See exactly what happened step-by-step
3. **Error Tracking**: Captures errors with full context
4. **Easy Export**: Get traces in JSON format to share

## Using the Trace Collector

### 1. View Recent Traces
```bash
# List all recent traces
./get_trace.py list

# List only error traces
./get_trace.py list --status error
```

### 2. Debug Specific Contact
```bash
# Quick debug for a contact
./get_trace.py debug z49hFQn0DxOX5sInJg60
```

### 3. Get Last Error
```bash
# Get the last error that occurred
./get_trace.py error

# Export for sharing
./get_trace.py error --raw > error.json
```

### 4. Real-Time Monitoring
```bash
# Watch traces as they happen
curl -N http://localhost:8000/debug/stream
```

### 5. Export for Claude
When something goes wrong:
```bash
# Get the last trace
./get_trace.py last --export > trace.json

# Or specific trace
./get_trace.py trace TRACE_ID --export > trace.json

# Then share trace.json with me!
```

## Web Interface

Access debug endpoints in your browser:

- http://localhost:8000/debug/health - Check trace collector status
- http://localhost:8000/debug/traces - View all traces
- http://localhost:8000/debug/last-error - See last error
- http://localhost:8000/debug/stats - Get statistics

## Example Trace Output

```json
{
  "trace_id": "z49hFQn0DxOX5sInJg60_20240120_143022_123456",
  "contact_id": "z49hFQn0DxOX5sInJg60", 
  "duration_ms": 3247,
  "status": "completed",
  "webhook_message": "Quiero agendar una cita",
  
  "timeline": [
    "[14:30:22] 📥 Received: 'Quiero agendar una cita'",
    "[14:30:22] 🧠 Intelligence: score=8",
    "[14:30:23] 🔀 Route: supervisor → sofia",
    "[14:30:24] 🔧 Tool: check_calendar_availability",
    "[14:30:25] 📤 Sent: '¡Perfecto! Tengo estos horarios...'"
  ],
  
  "summary": {
    "lead_score": 8,
    "suggested_agent": "sofia",
    "routing_path": ["supervisor → sofia"],
    "message_sent": true
  },
  
  "debug_hints": [
    "✅ Workflow completed successfully"
  ]
}
```

## Integration in Code

The tracing is already integrated! But if you want to add custom traces:

```python
from app.debug import trace_event, trace_error

# In your code
def my_function(state):
    trace_id = state.get("_trace_id", "unknown")
    
    # Log custom event
    trace_event(trace_id, "my_custom_event", {
        "data": "something important"
    })
    
    try:
        # Your logic
        result = do_something()
    except Exception as e:
        # Log errors with context
        trace_error(trace_id, "my_function", e, {
            "input": state
        })
        raise
```

## Benefits

1. **No More Guessing**: See exactly what happened
2. **Quick Debugging**: Share traces with me instantly
3. **Production Ready**: Low overhead, high value
4. **Easy to Use**: Simple CLI commands

## Next Steps

1. Deploy this update
2. When issues occur, run: `./get_trace.py last --export`
3. Share the JSON with me
4. I can debug immediately!

This makes debugging 10x faster! 🚀