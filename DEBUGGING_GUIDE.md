# 🔍 LangGraph Debugging & Observability Guide

This guide provides best practices for debugging LangGraph applications faster and more effectively.

## 1. Enable Enhanced Tracing

### LangSmith Tracing (Recommended)
```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"
os.environ["LANGCHAIN_PROJECT"] = "ghl-langgraph-agent"
```

### Add Custom Trace Metadata
```python
config = {
    "run_name": "debug_receptionist_error",
    "tags": ["production", "message_duplication"],
    "metadata": {
        "contact_id": contact_id,
        "deployment_id": "f71242bc-1ed1-4f23-9ef5-a1ce3a5b340c"
    }
}
graph.stream(inputs, config)
```

## 2. Use Debug Streaming Mode

### Stream in Debug Mode
```python
# Shows the complete state at each step
for chunk in graph.stream(inputs, stream_mode="debug"):
    print(f"Node: {chunk.get('name')}")
    print(f"State: {chunk.get('state')}")
    print(f"Outputs: {chunk.get('outputs')}")
    print("-" * 80)
```

### Stream with Subgraph Visibility
```python
# See outputs from nested graphs
for chunk in graph.stream(inputs, subgraphs=True, stream_mode="updates"):
    print(chunk)
```

## 3. Enhanced Logging in Nodes

### Add Detailed Logging to Each Node
```python
from app.utils.simple_logger import get_logger

logger = get_logger("node_name")

async def node_function(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("=== NODE STARTING ===")
    
    # Log input state
    logger.info(f"Input state keys: {list(state.keys())}")
    logger.info(f"Input messages: {len(state.get('messages', []))}")
    
    # Log critical values
    logger.info(f"Contact ID: {state.get('contact_id')}")
    logger.info(f"Thread ID: {state.get('thread_id')}")
    
    try:
        # Your logic here
        result = process_state(state)
        
        # Log outputs
        logger.info(f"Output messages: {len(result.get('messages', []))}")
        logger.info("=== NODE COMPLETE ===")
        return result
        
    except Exception as e:
        logger.error(f"Node error: {str(e)}", exc_info=True)
        # Log the full state on error
        logger.error(f"State at error: {json.dumps(state, default=str)}")
        raise
```

## 4. State Inspection Tools

### Get State at Any Point
```python
# Get current state
snapshot = graph.get_state(config)
print(f"Current node: {snapshot.next}")
print(f"State values: {snapshot.values}")
print(f"Messages: {len(snapshot.values.get('messages', []))}")

# Get state history
for state in graph.get_state_history(config):
    print(f"Checkpoint: {state.config['configurable']['checkpoint_id']}")
    print(f"Messages: {len(state.values.get('messages', []))}")
```

### Create State Validation Functions
```python
def validate_state(state: Dict[str, Any], node_name: str):
    """Validate state consistency"""
    messages = state.get('messages', [])
    
    # Check for duplicates
    contents = [msg.content if hasattr(msg, 'content') else msg.get('content', '') 
                for msg in messages]
    duplicates = len(contents) - len(set(contents))
    
    if duplicates > 0:
        logger.warning(f"{node_name}: Found {duplicates} duplicate messages!")
    
    # Check message types
    for msg in messages:
        if isinstance(msg, dict) and not msg.get('type') and not msg.get('role'):
            logger.error(f"{node_name}: Message missing type/role: {msg}")
    
    return duplicates == 0
```

## 5. Debug with Breakpoints

### Static Breakpoints
```python
# Compile with breakpoints
graph = workflow_graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["receptionist", "supervisor"],
    interrupt_after=["intelligence"]
)

# Run until breakpoint
result = graph.invoke(initial_state, config)

# Inspect state at breakpoint
state = graph.get_state(config)
print(f"Stopped before: {state.next}")

# Resume
result = graph.invoke(None, config)
```

### Dynamic Interrupts in Nodes
```python
def debug_node(state: State):
    if state.get('debug_mode'):
        # Pause for inspection
        value = interrupt({
            "state": state,
            "action": "Inspect state and continue"
        })
    return state
```

## 6. Message Flow Analysis

### Track Message Accumulation
```python
def analyze_message_flow(trace_id: str):
    """Analyze how messages accumulate through nodes"""
    client = Client()
    run = client.read_run(trace_id)
    
    child_runs = list(client.list_runs(
        project_id=run.session_id,
        filter=f'eq(parent_run_id, "{trace_id}")'
    ))
    
    child_runs.sort(key=lambda x: x.start_time)
    
    accumulation = []
    for child in child_runs:
        input_count = len(child.inputs.get('messages', []))
        output_count = len(child.outputs.get('messages', []))
        
        accumulation.append({
            'node': child.name,
            'input': input_count,
            'output': output_count,
            'delta': output_count - input_count
        })
    
    # Visualize accumulation pattern
    running_total = 0
    for item in accumulation:
        running_total += max(0, item['delta'])
        print(f"{item['node']:15} | In: {item['input']:3} | Out: {item['output']:3} | Total: {running_total:3}")
    
    return accumulation
```

## 7. Local Testing with Mock Data

### Create Test Fixtures
```python
async def test_receptionist_with_mock_data():
    """Test receptionist with different input patterns"""
    
    test_cases = [
        {
            "name": "webhook_pattern",
            "state": {
                "messages": [],
                "webhook_data": {"body": "Hola"},
                "contact_id": "test-123"
            }
        },
        {
            "name": "direct_invocation",
            "state": {
                "messages": [HumanMessage(content="Hola")],
                "contact_id": "test-123"
            }
        }
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test['name']}")
        try:
            result = await receptionist_node(test['state'])
            print(f"✅ Success: {len(result.get('messages', []))} messages returned")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
```

## 8. Production Debugging

### Add Debug Headers to Webhook
```python
@app.post("/webhook/message")
async def message_webhook(request: Request):
    # Add trace ID for correlation
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    
    logger.info(
        "Webhook received",
        trace_id=trace_id,
        headers=dict(request.headers),
        body_size=len(await request.body())
    )
    
    # Process with trace ID in config
    config = {
        "configurable": {"thread_id": thread_id},
        "run_id": trace_id,
        "metadata": {"source": "webhook", "trace_id": trace_id}
    }
```

### Monitor Key Metrics
```python
from typing import Dict
import time

class PerformanceMonitor:
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    async def monitor_node(self, node_name: str, node_func, state):
        start_time = time.time()
        input_msgs = len(state.get('messages', []))
        
        try:
            result = await node_func(state)
            duration = time.time() - start_time
            output_msgs = len(result.get('messages', []))
            
            self.metrics.setdefault(node_name, []).append({
                'duration': duration,
                'input_msgs': input_msgs,
                'output_msgs': output_msgs,
                'msg_delta': output_msgs - input_msgs,
                'success': True
            })
            
            if duration > 1.0:
                logger.warning(f"{node_name} took {duration:.2f}s")
            
            return result
            
        except Exception as e:
            self.metrics.setdefault(node_name, []).append({
                'duration': time.time() - start_time,
                'error': str(e),
                'success': False
            })
            raise
```

## 9. Common Issues Checklist

### When Debugging Message Duplication:
1. Check state reducer definition: `Annotated[List[BaseMessage], lambda x, y: x + y]`
2. Verify nodes use MessageManager or return only new messages
3. Check for dict vs BaseMessage comparison issues
4. Verify error handlers don't bypass deduplication
5. Check deployment has latest code (commit hash matches)

### Quick Debug Commands:
```python
# Check deployment version
print(f"Deployment: {deployment_id}")
print(f"Commit: {commit_hash}")
print(f"Trace time: {trace_time}")

# Verify message types
for msg in messages:
    print(f"Type: {type(msg)}, Content: {msg.content if hasattr(msg, 'content') else msg}")

# Check for error patterns
if any("Error" in str(msg) for msg in messages):
    print("⚠️ Error messages detected!")
```

## 10. Automated Testing

### Create Integration Tests
```python
import pytest

@pytest.mark.asyncio
async def test_workflow_no_duplication():
    """Test that messages don't duplicate through workflow"""
    
    initial_state = {
        "messages": [HumanMessage(content="Test message")],
        "contact_id": "test-123",
        "thread_id": "test-thread"
    }
    
    result = await workflow.ainvoke(initial_state)
    
    # Check no duplication
    messages = result.get('messages', [])
    contents = [m.content for m in messages if hasattr(m, 'content')]
    
    assert len(contents) == len(set(contents)), "Found duplicate messages!"
    assert len(messages) < 10, f"Too many messages: {len(messages)}"
```

## Summary

By implementing these debugging practices, you can:
- 🔍 See exactly what's happening at each step
- 📊 Track message flow and accumulation
- 🐛 Catch errors with detailed context
- ⚡ Test locally before deployment
- 📈 Monitor performance and patterns

Always remember to:
- Enable LangSmith tracing in production
- Add comprehensive logging to nodes
- Validate state between nodes
- Test with different input patterns
- Monitor deployment versions