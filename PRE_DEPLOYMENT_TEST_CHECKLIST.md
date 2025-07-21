# Pre-Deployment Test Checklist

## MANDATORY: Run Before EVERY Deployment

### 1. Test All Customer Types
```bash
# New customer - simple greeting
python test_production_scenario.py --type new --message "hola"
# Expected: Score 2, Maria responds

# Returning customer - simple greeting  
python test_production_scenario.py --type returning --message "hola"
# Expected: Score 2-3, NOT 6!

# Returning customer - business context
python test_production_scenario.py --type returning --message "necesito ayuda con mi restaurante"
# Expected: Score 4-6, Carlos responds
```

### 2. Test Score Ranges
- [ ] Score 1-2: Simple greeting → Maria
- [ ] Score 3-4: Name + greeting → Maria  
- [ ] Score 5-6: Business mentioned → Carlos
- [ ] Score 7-8: Business + problem → Sofia
- [ ] Score 9-10: Ready to buy → Sofia

### 3. Test Historical Context
- [ ] Empty history: Works correctly
- [ ] With history: No over-scoring
- [ ] Business in history + "hola": Score stays low
- [ ] Business in history + business question: Appropriate boost

### 4. Test Data Extraction
- [ ] "hola" → No business extraction
- [ ] "tengo un restaurante" → Extracts "restaurante"
- [ ] "10:00 AM" → No budget extraction
- [ ] "$300 al mes" → Extracts budget

### 5. Test Debug Messages
- [ ] Run full conversation flow
- [ ] Check final output has NO debug messages
- [ ] Verify only agent responses are sent

### 6. Test with Production Data
```python
# Use REAL contact IDs that have history
TEST_CONTACTS = {
    "new_customer": "abc123",  # No history
    "returning_basic": "def456",  # Has history, said "hola" before
    "returning_business": "ghi789"  # Has business discussions
}
```

### 7. Regression Tests
After EVERY fix, test that previous fixes still work:
- [ ] Thread filtering (not loading old conversations)
- [ ] Intelligence extraction (current message only)
- [ ] Debug message filtering
- [ ] Note creation
- [ ] Score persistence

## Quick Test Script
```bash
# Create this script: test_all_scenarios.py
scenarios = [
    {"type": "new", "message": "hola", "expected_score": 2},
    {"type": "returning", "message": "hola", "expected_score": 3},
    {"type": "returning", "message": "mi restaurante", "expected_score": 5},
    # ... add all scenarios
]

for scenario in scenarios:
    result = test_scenario(scenario)
    if result.score != scenario.expected_score:
        print(f"❌ FAILED: {scenario}")
        sys.exit(1)
```

## The Golden Rule
**"If you didn't test it with production-like data, it WILL break in production"**