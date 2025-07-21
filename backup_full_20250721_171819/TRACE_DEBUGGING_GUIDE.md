# Trace Debugging Guide - What to Check

## Access Your Traces

1. Go to https://smith.langchain.com
2. Navigate to your project: `ghl-langgraph-migration`
3. Look for traces after **10:04 AM CDT July 21, 2025**

## What to Look For

### 1. Language Detection Issues
Check for these patterns in your traces:

**✅ GOOD (After deployment)**
```json
{
  "conversation_analysis": {
    "language": "es",  // Should stay "es" throughout
    "message": "Hola, necesito ayuda"
  }
}
```

**❌ BAD (Before fix)**
```json
{
  "conversation_analysis": {
    "language": "en",  // Switched to English incorrectly
    "message": "Hola, necesito ayuda"
  }
}
```

### 2. Context Blindness Issues
Look for these in the supervisor brain node:

**✅ GOOD (After fix)**
```json
{
  "extracted_data": {
    "name": "Jaime",
    "business_type": "restaurante",
    "from_history": true  // Shows it loaded from history
  }
}
```

**❌ BAD (Before fix)**
```json
{
  "extracted_data": {},  // Empty, didn't load history
  "score": 2  // Low score for returning customer
}
```

### 3. Common Error Patterns

#### Language Switching
- **Symptom**: Customer writes in Spanish, agent responds in English
- **Check**: `conversation_analyzer` node output
- **Fixed**: Language detection now only analyzes customer messages

#### Missing Context
- **Symptom**: "¿Cuál es tu nombre?" asked to returning customers
- **Check**: `receptionist_simple` node - should load conversation history
- **Fixed**: Conversation analyzer processes historical messages

#### Wrong Agent Routing
- **Symptom**: Business owners sent to Maria instead of Carlos/Sofia
- **Check**: `supervisor_brain` node - look at score and routing
- **Fixed**: AI analyzer as fallback for complex Spanish

### 4. Deployment Verification

Your latest deployment includes:
1. **Language Detection Fix** (8907349)
   - Only analyzes customer messages
   - Maintains Spanish throughout

2. **AI-Enhanced Supervisor** (8e72b1f)
   - Better Spanish understanding
   - Handles "estoy perdiendo restaurantes"

3. **Context Loading Fix** (d35db4c)
   - Loads conversation history
   - Recognizes returning customers

### 5. Quick Test Messages

Test these messages and check the traces:

**Test 1: Spanish Persistence**
```
"Hola, necesito ayuda con mi restaurante"
```
- Should respond in Spanish
- Language should stay "es"

**Test 2: Business Recognition**
```
"Estoy perdiendo clientes en mi restaurante"
```
- Should route to Carlos/Sofia (score 5+)
- Should extract "restaurante" as business

**Test 3: Returning Customer**
```
First: "Me llamo Carlos"
Second: "Tengo un restaurante"
```
- Second message should remember "Carlos"
- Should not ask for name again

## Trace IDs to Investigate

If you see issues, look for:
1. The `conversation_analyzer` node output
2. The `supervisor_brain` node decisions
3. The `receptionist_simple` history loading
4. The final agent response language

## Need Help?

If you find specific trace IDs with issues:
1. Note the trace ID
2. Check which node has the problem
3. Look at the timestamp (pre/post deployment)
4. Share the specific error pattern