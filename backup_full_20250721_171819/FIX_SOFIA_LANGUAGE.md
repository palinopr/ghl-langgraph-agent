# Fix for Sofia Speaking English

## Issues Found

1. **Sofia is responding in English**: "Great! I need your email to send the calendar invite"
2. **Messages marked as "Unsuccessful"** in GHL
3. **Maria keeps repeating questions** about business type

## Root Causes

### 1. Sofia's Prompt Has English Examples
In `app/agents/sofia_agent_v2_fixed.py`, the prompt contains English response examples:
```python
- "Great! I need your email to send the calendar invite."
```

### 2. No Language Specification
The prompt doesn't explicitly tell Sofia to respond in Spanish.

### 3. Message Delivery Issues
"Unsuccessful" status suggests GHL API errors or rate limiting.

## Fixes Required

### 1. Update Sofia's Prompt (sofia_agent_v2_fixed.py)
Add at the beginning of the system prompt:
```python
CRITICAL: You MUST respond ONLY in Spanish. Never respond in English.
IMPORTANTE: Debes responder SOLO en español. Nunca respondas en inglés.
```

Replace English examples with Spanish:
```python
# Instead of:
- "Great! I need your email to send the calendar invite."

# Use:
- "¡Perfecto! Necesito tu correo electrónico para enviarte el enlace de la reunión."
- "¡Excelente! ¿Cuál es tu email para enviarte la invitación?"
```

### 2. Fix for Unsuccessful Messages
Check in `app/tools/ghl_client.py`:
- Rate limiting
- API response errors
- Message format issues

### 3. Fix for Repeated Questions
In `app/agents/maria_agent_v2.py`:
- Ensure Maria checks `extracted_data` properly
- Don't ask for business if already collected

## Quick Test After Fix
```bash
# Test Sofia in Spanish
python test_with_real_ghl.py "CONTACT_ID" "Sí, confirmo el presupuesto de $500"

# Should respond in Spanish asking for email
```

## Deployment Checklist
1. [ ] Update Sofia's prompt to Spanish-only
2. [ ] Replace all English examples with Spanish
3. [ ] Add error handling for GHL message sending
4. [ ] Verify Maria uses extracted_data correctly
5. [ ] Test locally before deploying