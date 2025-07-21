# How to Test Locally - No More 20-Minute Deploy Cycles! 🚀

## Quick Start

### 1. Test Any Message Instantly
```bash
# Test a specific message
python quick_test.py "tengo un negocio"

# Or use make
make test-specific
# Then type: tengo un negocio
```

### 2. Interactive Chat Testing
```bash
make test-interactive

# Then chat normally:
You: Hola
AI: ¡Hola! Soy de Main Outlet Media...
You: Jaime
AI: Mucho gusto, Jaime...
You: tengo un restaurante
AI: Excelente, para tu restaurante...
```

### 3. Test All Known Issues
```bash
make test-scenarios

# This tests:
# - Generic business terms (negocio)
# - Typos (reaturante)
# - Name extraction
# - Business acknowledgment
# - All production issues we've found
```

### 4. Pre-Deploy Check
```bash
make pre-deploy

# This runs:
# 1. Workflow validation (5 seconds)
# 2. All production scenarios
# Only deploys if everything passes!
```

## Common Test Cases

### Test Generic Business Term
```bash
python quick_test.py "tengo un negocio"
# Should ask for SPECIFIC business type
```

### Test Typo
```bash
python quick_test.py "tengo un reaturante"
# Should recognize as "restaurante"
```

### Test Name Extraction
```bash
python quick_test.py "Jaime"
# Should extract name
```

### Test Full Conversation
```bash
make test-interactive
# Then:
# You: Hola
# You: Maria
# You: tengo un restaurante
# You: estoy perdiendo clientes
# You: si, como 500 al mes
```

## Understanding the Output

### Good Output:
```
Testing message: 'tengo un negocio'
----------------------------------------
Extracted Data: {'business_type': None}  # ✅ Good - not extracting "negocio"
Lead Score: 3
Current Agent: maria
AI Response: ¿Qué tipo de negocio tienes?  # ✅ Good - asking for specific type
```

### Bad Output:
```
Testing message: 'tengo un negocio'
----------------------------------------
Extracted Data: {'business_type': 'negocio'}  # ❌ Bad - generic term extracted
Lead Score: 3
Current Agent: maria
AI Response: Para tu negocio...  # ❌ Bad - using generic term
```

## Debugging Tips

### 1. Check State at Any Time
In interactive mode:
```
You: state
📊 Current State:
  Extracted: {'name': 'Jaime', 'business_type': 'restaurante'}
  Score: 4
  Agent: maria
```

### 2. Reset Conversation
In interactive mode:
```
You: reset
🔄 Conversation reset
```

### 3. Test Edge Cases
```bash
# Empty business
python quick_test.py "tengo un"

# Multiple typos
python quick_test.py "tnego un resturante"

# Mixed language
python quick_test.py "I have un restaurante"
```

## Workflow Testing Process

### Before Any Code Change:
1. Run `make test-scenarios` to establish baseline
2. Make your changes
3. Run `make test-scenarios` again
4. All tests should still pass

### Before Deploying:
1. `make pre-deploy` - Must pass all tests
2. `git add -A`
3. `git commit -m "Your message"`
4. `git push` - Auto-validates before push

## Common Issues and Solutions

### Issue: Import Errors
```bash
# Make sure you're in the right directory
cd langgraph-ghl-agent

# Activate virtual environment
source venv_langgraph/bin/activate
# or
source venv313/bin/activate
```

### Issue: Workflow Not Found
```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue: Tests Failing After Changes
```bash
# Check what changed
git diff

# Revert if needed
git checkout -- file_that_broke.py
```

## Benefits of Local Testing

1. **Instant Feedback**: No 20-minute wait
2. **Test Specific Issues**: Focus on what you're fixing
3. **Catch Errors Early**: Before they hit production
4. **Confidence**: Know it works before deploying
5. **Faster Development**: 10x faster iteration

## Example Development Flow

1. Customer reports: "AI keeps asking for business type even when I say 'tengo un restaurante'"

2. Test locally:
   ```bash
   python quick_test.py "tengo un restaurante"
   ```

3. See the issue, make fix in code

4. Test again:
   ```bash
   python quick_test.py "tengo un restaurante"
   ```

5. Verify fix works

6. Run full test suite:
   ```bash
   make test-scenarios
   ```

7. Deploy with confidence:
   ```bash
   make deploy
   ```

Total time: 5 minutes instead of hours!

## Advanced Testing

### Test with Previous State
```python
# In test_locally.py, you can pass previous state:
previous_state = {
    "messages": [HumanMessage(content="Hola")],
    "extracted_data": {"name": "Jaime"},
    "lead_score": 3
}
asyncio.run(test_specific_issue("tengo un restaurante", previous_state))
```

### Batch Testing
Create a file `test_messages.txt`:
```
Hola
Jaime
tengo un negocio
tengo un restaurante
tengo un reaturante
```

Then:
```bash
while read msg; do
  echo "Testing: $msg"
  python quick_test.py "$msg"
  echo "---"
done < test_messages.txt
```

## Summary

No more deploy-wait-debug cycles! Test everything locally first:
- `make test-specific` - Test any message
- `make test-interactive` - Chat testing
- `make test-scenarios` - Test all known issues
- `make pre-deploy` - Final check before deploy

Happy testing! 🎉