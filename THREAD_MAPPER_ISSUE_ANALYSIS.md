# Thread Mapper Issue Analysis

## Critical Discovery

The thread_mapper IS working correctly at the state level, but LangGraph Cloud's checkpoint system ignores it!

### Evidence from Trace Analysis

**Trace 1 (Restaurant message):**
- Metadata thread_id: `887dbb15-d4ed-4c1d-ae13-c03e550fcf68` (UUID)
- State thread_id after mapper: `contact-daRK4gKoyQJ0tb6pB18u` ✅

**Trace 2 (Si message):**
- Metadata thread_id: `3798d672-14ac-4195-bfb6-329fd9c1cfe0` (Different UUID!)
- State thread_id after mapper: `contact-daRK4gKoyQJ0tb6pB18u` ✅

## The Core Problem

1. **Thread mapper works**: It correctly maps UUIDs to `contact-{id}` in the state
2. **LangGraph Cloud ignores it**: The checkpoint system uses the UUID from metadata, not the mapped thread_id
3. **Result**: Each message gets a different UUID, so no checkpoint persistence

## Why Current Solution Fails

The thread_mapper updates the state's thread_id, but LangGraph Cloud's infrastructure:
- Uses the metadata thread_id for checkpoint storage
- Doesn't respect the mapped thread_id in state
- Creates new UUIDs for each webhook call

## Needed Solution

We need to intercept at a lower level, possibly:
1. Override the checkpoint configuration
2. Use a custom checkpointer that maps UUIDs to our pattern
3. Find a way to set the thread_id in the invocation request itself

## Next Steps

1. Check if we can pass thread_id in the webhook invocation
2. Investigate custom checkpointer implementation
3. Look for LangGraph Cloud configuration options