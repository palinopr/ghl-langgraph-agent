# 🔍 COMPLETE LIVE DEBUGGING PLAN

## Overview
This plan provides comprehensive debugging for the live LangGraph GHL agent system to see EVERYTHING that happens during a conversation flow.

## 1. Enhanced Logging Strategy

### A. Add Debug Logging to Every Critical Point

```python
# In supervisor_brain_simple.py
logger.info("🎯 SUPERVISOR BRAIN ENTRY")
logger.info(f"  - Contact ID: {contact_id}")
logger.info(f"  - Current Message: '{current_message}'")
logger.info(f"  - Message Count: {len(messages)}")
logger.info(f"  - Previous Score: {previous_score}")
logger.info(f"  - Previous Business: {previous_business}")

# After extraction
logger.info("📊 EXTRACTION COMPLETE:")
logger.info(f"  - Extracted Name: {extracted.get('name')}")
logger.info(f"  - Extracted Business: {extracted.get('business_type')}")
logger.info(f"  - Extracted Budget: {extracted.get('budget')}")

# Before routing
logger.info("🚦 ROUTING DECISION:")
logger.info(f"  - Final Score: {final_score}")
logger.info(f"  - Next Agent: {next_agent}")
logger.info(f"  - Reason: {routing_reason}")
```

### B. Add Entry/Exit Logging to Each Agent

```python
# In each agent (sofia, carlos, maria)
logger.info(f"🤖 {AGENT_NAME} AGENT ENTRY")
logger.info(f"  - State Keys: {list(state.keys())}")
logger.info(f"  - Messages: {len(state.get('messages', []))}")
logger.info(f"  - Contact: {state.get('contact_id')}")

# Before response
logger.info(f"💬 {AGENT_NAME} RESPONSE: {response_text[:100]}...")
```

### C. Add Tool Call Logging

```python
# In agent_tools_v2.py
logger.info(f"🔧 TOOL CALLED: {tool_name}")
logger.info(f"  - Parameters: {params}")
logger.info(f"  - Contact: {contact_id}")

# After tool execution
logger.info(f"✅ TOOL RESULT: {result}")
```

## 2. State Tracking System

### A. Create State Snapshot Function

```python
def snapshot_state(state: dict, checkpoint: str) -> dict:
    """Capture complete state at key checkpoints"""
    snapshot = {
        "checkpoint": checkpoint,
        "timestamp": datetime.now().isoformat(),
        "contact_id": state.get("contact_id"),
        "lead_score": state.get("lead_score"),
        "extracted_data": state.get("extracted_data", {}),
        "messages_count": len(state.get("messages", [])),
        "last_message": state.get("messages", [])[-1].content if state.get("messages") else None,
        "appointment_booked": state.get("appointment_booked", False),
        "available_slots": len(state.get("available_slots", [])),
        "current_agent": state.get("current_agent"),
        "routing_count": state.get("routing_count", 0)
    }
    
    logger.info(f"📸 STATE SNAPSHOT at {checkpoint}:")
    logger.info(json.dumps(snapshot, indent=2))
    
    return snapshot
```

### B. Add Snapshots at Key Points

```python
# In workflow
snapshot_state(state, "RECEPTIONIST_EXIT")
snapshot_state(state, "SUPERVISOR_ENTRY")
snapshot_state(state, "SUPERVISOR_EXIT")
snapshot_state(state, "AGENT_ENTRY")
snapshot_state(state, "AGENT_EXIT")
snapshot_state(state, "RESPONDER_ENTRY")
```

## 3. Message Flow Tracker

### A. Create Message History Logger

```python
def log_conversation_flow(messages: list):
    """Log the complete conversation flow"""
    logger.info("💬 CONVERSATION FLOW:")
    for i, msg in enumerate(messages):
        role = "Human" if hasattr(msg, 'type') and msg.type == "human" else "AI"
        content = msg.content if hasattr(msg, 'content') else str(msg)
        logger.info(f"  {i+1}. {role}: {content[:100]}...")
```

### B. Track Message Sources

```python
# Add metadata to messages
message_metadata = {
    "source": "ghl_history" | "current_webhook" | "agent_response",
    "timestamp": datetime.now().isoformat(),
    "agent": "sofia" | "carlos" | "maria",
    "message_id": str(uuid.uuid4())
}
```

## 4. GHL API Call Tracker

### A. Log All GHL API Calls

```python
# In ghl_client.py
async def _make_request(self, method: str, endpoint: str, **kwargs):
    request_id = str(uuid.uuid4())
    
    logger.info(f"🌐 GHL API CALL [{request_id}]:")
    logger.info(f"  - Method: {method}")
    logger.info(f"  - Endpoint: {endpoint}")
    logger.info(f"  - Data: {kwargs.get('data', {})}")
    
    try:
        response = await self._original_make_request(method, endpoint, **kwargs)
        logger.info(f"✅ GHL API RESPONSE [{request_id}]:")
        logger.info(f"  - Status: Success")
        logger.info(f"  - Data: {response}")
        return response
    except Exception as e:
        logger.error(f"❌ GHL API ERROR [{request_id}]: {str(e)}")
        raise
```

## 5. Decision Point Tracker

### A. Log All Routing Decisions

```python
def log_routing_decision(state: dict, decision: str, reason: str):
    """Log routing decisions with full context"""
    logger.info("🚦 ROUTING DECISION POINT:")
    logger.info(f"  - Current Score: {state.get('lead_score')}")
    logger.info(f"  - Has Name: {bool(state.get('extracted_data', {}).get('name'))}")
    logger.info(f"  - Has Business: {bool(state.get('extracted_data', {}).get('business_type'))}")
    logger.info(f"  - Has Budget: {bool(state.get('extracted_data', {}).get('budget'))}")
    logger.info(f"  - Decision: Route to {decision}")
    logger.info(f"  - Reason: {reason}")
```

## 6. Error and Edge Case Tracking

### A. Wrap All Functions with Error Logging

```python
def debug_wrapper(func):
    """Wrapper to catch and log all errors"""
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        try:
            logger.info(f"➡️ Entering {func_name}")
            result = await func(*args, **kwargs)
            logger.info(f"✅ Exiting {func_name} successfully")
            return result
        except Exception as e:
            logger.error(f"❌ Error in {func_name}: {str(e)}")
            logger.error(f"  - Args: {args}")
            logger.error(f"  - Kwargs: {kwargs}")
            logger.error(traceback.format_exc())
            raise
    return wrapper
```

## 7. Live Testing Script

### A. Create Comprehensive Test Runner

```python
#!/usr/bin/env python3
"""
Live debugging test runner with full visibility
"""

async def test_with_full_debug(contact_id: str, messages: list):
    """Run a complete test with all debugging enabled"""
    
    print("🚀 STARTING LIVE DEBUG TEST")
    print(f"Contact: {contact_id}")
    print(f"Messages to send: {len(messages)}")
    
    for i, message in enumerate(messages):
        print(f"\n{'='*60}")
        print(f"📱 STEP {i+1}: Sending '{message}'")
        print("="*60)
        
        # Create webhook data
        webhook_data = {
            "id": contact_id,
            "contactId": contact_id,
            "message": message,
            "body": message,
            "type": "SMS",
            "locationId": "sHFG9Rw6BdGh6d6bfMqG",
            "direction": "inbound",
            "dateAdded": datetime.now().isoformat()
        }
        
        # Run workflow
        start_time = time.time()
        result = await run_workflow_safe(webhook_data)
        elapsed = time.time() - start_time
        
        print(f"\n⏱️ Execution Time: {elapsed:.2f}s")
        
        # Analyze result
        if result.get('status') == 'completed':
            state = result.get('state', {})
            
            print("\n📊 RESULT ANALYSIS:")
            print(f"  - Lead Score: {state.get('lead_score')}")
            print(f"  - Business Type: {state.get('extracted_data', {}).get('business_type')}")
            print(f"  - Budget: {state.get('extracted_data', {}).get('budget')}")
            print(f"  - Appointment Booked: {state.get('appointment_booked')}")
            
            # Get AI response
            messages = state.get('messages', [])
            for msg in reversed(messages):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                    print(f"\n🤖 AI Response: {msg.content}")
                    break
        else:
            print(f"\n❌ ERROR: {result.get('error')}")
        
        # Wait before next
        print("\n⏳ Waiting 3 seconds...")
        await asyncio.sleep(3)

# Test sequence
test_messages = [
    "Hola",
    "Jaime",
    "Restaurante",
    "No puedo responder rápido",
    "Sí",
    "jaime@test.com",
    "10:00 AM"
]

await test_with_full_debug("test_contact_123", test_messages)
```

## 8. Performance Monitoring

### A. Add Timing to Each Step

```python
class TimingContext:
    def __init__(self, name: str):
        self.name = name
        self.start = None
        
    def __enter__(self):
        self.start = time.time()
        logger.info(f"⏱️ Starting {self.name}")
        return self
        
    def __exit__(self, *args):
        elapsed = time.time() - self.start
        logger.info(f"⏱️ {self.name} took {elapsed:.3f}s")

# Usage
with TimingContext("Supervisor Analysis"):
    result = await analyze_lead(state)
```

## 9. Deployment Verification

### A. Version Tracking

```python
# Add to each file
__version__ = "1.0.1"  # Increment on changes

# Log version at startup
logger.info(f"🔢 Running version: {__version__}")
```

### B. Deployment Checker

```python
def verify_deployment():
    """Check if latest code is deployed"""
    expected_features = [
        "Enhanced business extraction",
        "Appointment booking with real slots",
        "Budget extraction fix for time patterns"
    ]
    
    for feature in expected_features:
        logger.info(f"✓ Feature present: {feature}")
```

## 10. Real-Time Monitoring Dashboard

### A. Create Status Endpoint

```python
@app.get("/debug/status/{contact_id}")
async def get_debug_status(contact_id: str):
    """Get current status and history for a contact"""
    return {
        "contact_id": contact_id,
        "current_score": get_current_score(contact_id),
        "extracted_data": get_extracted_data(contact_id),
        "conversation_length": get_message_count(contact_id),
        "last_agent": get_last_agent(contact_id),
        "appointment_status": get_appointment_status(contact_id),
        "recent_errors": get_recent_errors(contact_id),
        "workflow_traces": get_workflow_traces(contact_id)
    }
```

## Implementation Steps

1. **Add all logging enhancements** to see every decision
2. **Deploy with debug mode enabled**
3. **Run test sequence** with known inputs
4. **Monitor logs in real-time**
5. **Analyze any discrepancies**
6. **Fix issues and redeploy**

## Expected Output

With this debugging plan, you'll see:
- Every message received and sent
- Every extraction attempt and result
- Every routing decision and reason
- Every API call to GHL
- Every tool invocation
- Every state change
- Complete timing information
- Any errors with full context

This will give you COMPLETE visibility into what's happening in the live system!