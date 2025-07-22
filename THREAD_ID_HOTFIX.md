# Thread ID Consistency Hotfix

## 🚨 Critical Issue Fixed
The system was creating a new thread_id for every message, causing agents to forget conversation history between messages.

## 📋 The Problem
Debug analysis revealed each message from the same contact had different thread_ids:
```
Trace 1: thread_id: d779d1e2-ee2c-458d-8ce6-8828d106ad7f
Trace 2: thread_id: 0dbc1c79-30eb-4a12-9509-dbd17eb0d4bd (DIFFERENT!)
Trace 3: thread_id: 3969eb20-54d1-41a9-a201-2da88df6a578 (DIFFERENT!)
Trace 4: thread_id: c95ee525-421e-4810-8887-4bd2ce0e4746 (DIFFERENT!)
```

This caused:
- Maria asking for names repeatedly
- No conversation memory between messages
- Lost context and extracted data
- Poor user experience

## ✅ The Fix

### File: `app/workflow.py` (lines 213-219)

**Before:**
```python
thread_id = webhook_data.get("conversationId") or webhook_data.get("threadId")
```

**After:**
```python
# Use GHL conversationId as thread_id for consistency
thread_id = (
    webhook_data.get("conversationId") or  # GHL conversation ID
    webhook_data.get("threadId") or        # Fallback to threadId
    f"contact-{contact_id}"                # Last resort: contact-based
)
logger.info(f"Using thread_id: {thread_id} for contact: {contact_id}")
```

### Also Updated Config (line 238)
```python
config={"configurable": {"thread_id": thread_id}}  # Use consistent thread_id
```

## 🧪 Test Results

All tests passed! Same contact now maintains same thread_id:

### Test 1: With conversationId ✅
```
webhook1: {"contactId": "test123", "conversationId": "conv-abc", "body": "Hola"}
webhook2: {"contactId": "test123", "conversationId": "conv-abc", "body": "Jaime"}
Result: Both use thread_id: "conv-abc"
```

### Test 2: With threadId fallback ✅
```
webhook1: {"contactId": "test456", "threadId": "thread-xyz", "body": "Hola"}
webhook2: {"contactId": "test456", "threadId": "thread-xyz", "body": "Restaurante"}
Result: Both use thread_id: "thread-xyz"
```

### Test 3: Contact-based fallback ✅
```
webhook1: {"contactId": "test789", "body": "Hola"}
webhook2: {"contactId": "test789", "body": "Mi presupuesto es $500"}
Result: Both use thread_id: "contact-test789"
```

## 📊 Impact

### Before Fix:
- Each message = new conversation
- No memory between messages
- Repetitive questions
- Score regression

### After Fix:
- Consistent thread_id per conversation
- Full conversation memory
- Context preserved
- Progressive scoring

## 🚀 Deployment

This is a critical hotfix that should be deployed immediately:

1. **Commit Message**:
```
🚨 HOTFIX: Ensure thread_id consistency for conversation memory

Critical fix for conversation continuity issue where each message
was getting a new thread_id, causing complete memory loss between messages.

## Problem
- Each webhook created random thread_id
- Agents forgot everything between messages
- Maria kept asking for names repeatedly
- Users frustrated with repetitive questions

## Solution
- Use GHL conversationId as primary thread_id
- Fallback to threadId if no conversationId
- Last resort: use contact-based thread_id
- Added debug logging for thread_id tracking

## Testing
- ✅ Same conversationId keeps same thread_id
- ✅ Same threadId keeps same thread_id  
- ✅ Same contact keeps same thread_id
- ✅ All fallback patterns tested

This fixes the #1 user complaint about agents forgetting context!
```

2. **Test Command**:
```bash
python test_thread_id_fix.py
```

3. **Verification**:
- Check logs for: `Using thread_id: {id} for contact: {contact}`
- Verify same thread_id across multiple messages
- Test conversation continuity

## 🎯 Result

With this fix, agents will now:
- Remember previous messages in the conversation
- Build on extracted data progressively
- Maintain context throughout the conversation
- Provide a much better user experience

The thread_id consistency issue was the root cause of agents appearing to have "amnesia" between messages!