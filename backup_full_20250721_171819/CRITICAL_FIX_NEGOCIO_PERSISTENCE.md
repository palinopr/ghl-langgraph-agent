# CRITICAL FIX: "negocio" Persistence Issue

## The Problem
Even after our fix, "negocio" is still appearing because:
1. It was extracted BEFORE our fix deployed
2. It's being persisted in state["extracted_data"]
3. The analyzer merges current extraction with previous data

## The Flow:
1. Message 1: "Hola" → Extracts nothing, but MERGES with previous state containing "negocio"
2. Message 2: "tengo un restaurante" → Should extract "restaurante" but previous "negocio" persists

## Solutions:

### Option 1: Never Persist Generic Terms (BEST)
Add validation AFTER merging to remove generic terms:

```python
# After line 543 in analyzer.py
extracted = self.extractor.extract_all(current_message, previous_data)

# CRITICAL: Remove generic business terms that should never persist
if extracted.get("business_type") in ["negocio", "empresa", "local", "comercio"]:
    extracted["business_type"] = None
```

### Option 2: Clear State for New Conversations
Ensure new conversations don't inherit old extracted data

### Option 3: Fix at GHL Level
Clear the custom fields storing generic terms

## Quick Fix to Deploy:
We need to add the validation AFTER the merge to ensure generic terms never persist in state.