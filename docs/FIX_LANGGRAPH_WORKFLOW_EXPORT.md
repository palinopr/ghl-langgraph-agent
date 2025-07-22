# Fix: LangGraph Workflow Export Error

## Problem
LangGraph deployment failed with:
```
ValueError: Variable 'workflow' in module '/deps/__outer_ghl-langgraph-agent/src/app/workflow.py' is not a Graph or Graph factory function
```

The workflow was being set to `None` at module level and only created when `run_workflow()` was called.

## Solution
Created a synchronous workflow at module import time that LangGraph can use:

1. **Added `create_sync_workflow()` function**:
   - Creates the same workflow graph structure
   - Uses synchronous `SqliteSaver` instead of async
   - Compiles and returns a `CompiledStateGraph` object

2. **Module-level export**:
   ```python
   # Before: workflow = None
   # After: 
   workflow = create_sync_workflow()
   ```

3. **Preserved async functionality**:
   - `run_workflow()` still uses `AsyncSqliteSaver` for runtime
   - No changes to webhook processing logic

## Key Changes
- Import both `SqliteSaver` (sync) and `AsyncSqliteSaver` (async)
- Create compiled workflow at module import time
- LangGraph now finds a proper Graph object when importing

## Validation
```bash
# Workflow is now a compiled Graph object
Workflow type: <class 'langgraph.graph.state.CompiledStateGraph'>
Has invoke method: True
✅ Workflow is a compiled Graph object!
```

The deployment error should now be resolved!