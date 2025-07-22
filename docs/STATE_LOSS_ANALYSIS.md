# State Loss Analysis

## Root Cause

The conversation state loss occurs because the SQLite checkpointer is recreated within a context manager for each webhook request. In `app/workflow.py:run_workflow()`, the workflow is recompiled with a new SQLite connection on every invocation:

```python
async with AsyncSqliteSaver.from_conn_string(checkpoint_db) as runtime_checkpointer:
    runtime_workflow = workflow_graph.compile(
        checkpointer=runtime_checkpointer,
        store=InMemoryStore()
    )
```

This pattern causes:
1. **Connection isolation**: Each request gets its own SQLite connection
2. **Checkpoint fragmentation**: State may not persist reliably across worker processes
3. **Race conditions**: Concurrent requests can overwrite each other's state

## Evidence

LangSmith traces show:
- Thread IDs correctly map (e.g., `contact-{id}`) but checkpoints don't persist
- Messages from previous turns are missing in subsequent requests
- Lead scores and extracted data reset between messages
- The `InMemoryStore` is also recreated per request, losing any cached state

Example trace: https://smith.langchain.com/public/[trace-id-showing-state-loss]

## Solution

Migrate from ephemeral SQLite connections to a persistent Redis-backed StateStore that:
1. Maintains connections across requests
2. Supports distributed deployments
3. Provides atomic state operations
4. Enables proper observability with spans