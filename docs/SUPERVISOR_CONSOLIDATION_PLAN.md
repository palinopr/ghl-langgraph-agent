# Supervisor Consolidation Plan

## Current State Analysis

### Active in Production
- **File**: `app/agents/supervisor.py`
- **Import**: Used in `app/workflow.py` as `supervisor_node`
- **Status**: Already has the handoff fixes without InjectedState

### Not Used in Production
- **File**: `app/agents/supervisor_official.py`
- **Import**: Not used in workflow, but exported in `__init__.py`
- **Status**: Just fixed to remove InjectedState

## Consolidation Steps

### Step 1: Verify supervisor.py has all fixes
The current `supervisor.py` already has the correct pattern without InjectedState.

### Step 2: Remove supervisor_official.py
Since production uses `supervisor.py`, we should remove the duplicate.

### Step 3: Update __init__.py
Remove the export of `supervisor_official_node`.

### Step 4: Fix remaining_steps warning
Add default value in state initialization wherever agents are invoked.

### Step 5: Fix agent_tools_modernized.py
Remove InjectedState from 5 tools:
- `escalate_to_supervisor`
- `get_contact_details_with_task`
- `update_contact_with_context`
- `book_appointment_with_instructions`
- `save_important_context`

## Implementation Priority

1. **CRITICAL**: Fix `agent_tools_modernized.py` - These tools are actively used and may cause validation errors
2. **HIGH**: Remove `supervisor_official.py` - Prevent confusion
3. **MEDIUM**: Fix `remaining_steps` warning - Cosmetic but should be fixed
4. **LOW**: Update documentation

## Risk Assessment

- **Low Risk**: Removing `supervisor_official.py` since it's not used in production
- **Medium Risk**: Fixing tools in `agent_tools_modernized.py` - need careful testing
- **No Risk**: Adding `remaining_steps` to state initialization