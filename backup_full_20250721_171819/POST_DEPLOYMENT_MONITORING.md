# Post-Deployment Monitoring Guide

## Deployment Complete! 🚀

**Commit Hash**: a5f10ff
**Deployment Time**: July 21, 2025, 12:58 PM CDT

## What to Monitor in LangSmith

### 1. Check Agent Data Usage
Look for traces where agents are using extracted data:
- Search for traces with "extracted_data" in the state
- Verify agents aren't asking for already-provided information
- Confirm natural conversation flow

### 2. Verify Fuzzy Matching
Monitor business extraction with typos:
- Look for words like "reaturante", "resturante", "gimansio"
- Check if they're correctly mapped to proper business types
- Verify confidence scores in logs

### 3. Test Scenarios

#### Test 1: Name Already Provided
```
Customer: "Hola, soy María"
Expected: Agent should say "Hola María!" NOT "¿Cuál es tu nombre?"
```

#### Test 2: Business with Typo
```
Customer: "tengo un reaturante"
Expected: System should detect "restaurante" and increase score
```

#### Test 3: Complete Information
```
Customer: "Hola, soy Carlos y tengo una barbería"
Expected: Agent should skip name and business questions, go to problem/goal
```

## Key Metrics to Track

1. **Conversation Length**
   - Should be shorter (no repeated questions)
   - More direct progression through stages

2. **Score Accuracy**
   - "Hola" = 2-3 (not 6)
   - Business mentions = appropriate boost
   - Typos should still trigger scoring

3. **Agent Behavior**
   - Check if Maria/Carlos/Sofia use extracted_data
   - Verify they acknowledge what's already known
   - No more "What's your name?" after name given

## LangSmith Queries

### Find Recent Traces
```python
from langsmith import Client
from datetime import datetime, timezone

client = Client()
deployment_time = datetime(2025, 7, 21, 17, 58, 0, tzinfo=timezone.utc)  # 12:58 PM CDT

runs = list(client.list_runs(
    project_name="ghl-langgraph-agent",
    limit=50,
    execution_order=1,
    start_time=deployment_time
))

for run in runs:
    print(f"ID: {run.id}")
    if run.inputs and 'messages' in run.inputs:
        last_msg = run.inputs['messages'][-1]['content'] if run.inputs['messages'] else ""
        print(f"Message: {last_msg[:50]}...")
```

### Check for Repeated Questions
```python
# Look for patterns of agents asking for already-provided info
for run in runs:
    if run.outputs:
        output = str(run.outputs).lower()
        if "¿cuál es tu nombre?" in output:
            # Check if name was already in extracted_data
            if run.inputs.get('extracted_data', {}).get('name'):
                print(f"❌ Agent asked for name when already known: {run.id}")
```

## Expected Results

### Before Fix
- Agent asks "¿Cuál es tu nombre?" even after customer says "Jaime"
- "reaturante" gets score 1 (not recognized)
- Conversations loop with repeated questions

### After Fix
- Agent says "Hola Jaime!" when name is provided
- "reaturante" detected as "restaurante" (fuzzy matching)
- Natural progression without repeated questions

## Troubleshooting

If issues persist:

1. **Check Fuzzy Extractor Loading**
   - Look for warning: "Fuzzy extractor not available"
   - Verify rapidfuzz is installed in deployment

2. **Verify State Passing**
   - Check if extracted_data is in agent state
   - Look for extraction logs in intelligence node

3. **Monitor Responder**
   - Use enhanced debugging to track message sending
   - Check response_sent field in state

## Success Indicators

✅ Shorter conversations (no loops)
✅ Natural acknowledgment of provided info
✅ Typos handled gracefully
✅ Correct lead scoring (1-10 scale)
✅ Happy customers (no frustration from repeated questions)

## Next Steps

1. Monitor for 24 hours
2. Collect trace IDs of any issues
3. Verify fuzzy matching is working
4. Check responder message delivery
5. Gather customer feedback

## Contact for Issues

If you notice any problems:
1. Collect trace IDs
2. Note the specific issue
3. Document expected vs actual behavior