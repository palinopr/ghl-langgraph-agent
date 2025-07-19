# Maria Hardcoded Conversation Flow Fix

## Problem
Maria was still repeating "¿Qué tipo de negocio tienes?" even after:
1. The user already answered "Restaurante"
2. The supervisor correctly detected the business type
3. The conversation enforcer provided the correct next response

## Root Cause
Maria's prompt had HARDCODED conversation examples that were overriding the conversation enforcer's instructions:

```
Step 2 - NAME RESPONSE:
Customer: "Jaime" → You: "Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"
```

Even though the conversation enforcer was providing:
```
ALLOWED RESPONSE: "Ya veo, restaurante. ¿Cuál es tu mayor desafío con los mensajes de WhatsApp?"
```

Maria was following the hardcoded examples instead of the allowed response.

## Solution
Updated Maria's prompt to:
1. Add CRITICAL warnings to use ONLY the allowed response
2. Replace hardcoded examples with general flow guidance
3. Emphasize that the conversation enforcer determines exact responses

### Changes Made:
1. Added stronger enforcement instructions:
   ```
   ⚡ CRITICAL: You MUST use the EXACT allowed response above!
   ⚡ IGNORE the example conversation flow below - use ONLY the allowed response!
   ```

2. Replaced hardcoded examples with guidance:
   ```
   CONVERSATION FLOW GUIDANCE:
   ⚠️ IMPORTANT: The EXACT responses are determined by the conversation enforcer above!
   ⚠️ Use the "ALLOWED RESPONSE" provided - DO NOT use these examples literally!
   ```

## Impact
- Maria will now use the conversation enforcer's allowed response
- No more repeated questions when information was already provided
- Conversation will flow naturally based on actual state

## Testing
Test the specific scenario:
1. User says "Restaurante" after being asked for business type
2. Maria should respond: "Ya veo, restaurante. ¿Cuál es tu mayor desafío..."
3. NOT: "Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"