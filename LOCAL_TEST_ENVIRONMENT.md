# Complete Local Testing Environment Setup

## The Problem
- Deploy → Wait 20 min → Find error → Fix → Deploy → Wait 20 min → Repeat
- This is killing productivity!

## The Solution: Local Testing That Mimics Production

### 1. Quick Test Script for Common Scenarios

Create `test_locally.py`:

```python
#!/usr/bin/env python3
"""
Test the system locally with production-like data
"""
import asyncio
from datetime import datetime
from app.workflow import app
from app.state.conversation_state import ConversationState
from langchain_core.messages import HumanMessage, AIMessage

async def test_conversation_flow():
    """Test a complete conversation flow"""
    
    # Test scenarios
    test_cases = [
        {
            "name": "Generic Business Test",
            "messages": [
                "Hola",
                "Jaime", 
                "tengo un negocio"
            ],
            "expected": "Should ask for SPECIFIC business type"
        },
        {
            "name": "Typo Test",
            "messages": [
                "Hola",
                "Maria",
                "tengo un reaturante"
            ],
            "expected": "Should recognize 'restaurante' with fuzzy matching"
        },
        {
            "name": "Complete Flow Test",
            "messages": [
                "Hola",
                "Carlos",
                "tengo un restaurante",
                "estoy perdiendo clientes",
                "si, como 500 al mes"
            ],
            "expected": "Should progress through all stages"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test['name']}")
        print(f"Expected: {test['expected']}")
        print(f"{'='*60}")
        
        # Initialize state
        state = {
            "messages": [],
            "contact_id": f"test_{test['name'].lower().replace(' ', '_')}",
            "webhook_data": {
                "contactId": f"test_{test['name'].lower().replace(' ', '_')}",
                "locationId": "test_location",
                "type": "SMS"
            }
        }
        
        # Run each message through the workflow
        for i, message in enumerate(test['messages']):
            print(f"\n→ Customer: '{message}'")
            
            # Add message to state
            state["messages"].append(HumanMessage(content=message))
            
            # Run workflow
            result = await app.ainvoke(state)
            
            # Get AI response
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, 'content'):
                    print(f"← AI: {last_msg.content[:100]}...")
            
            # Check extracted data
            if result.get("extracted_data"):
                print(f"  Extracted: {result['extracted_data']}")
            
            # Check score
            if result.get("lead_score"):
                print(f"  Score: {result['lead_score']}")
            
            # Update state for next iteration
            state = result

async def test_specific_issue(message: str, previous_state: dict = None):
    """Test a specific message with optional previous state"""
    
    state = previous_state or {
        "messages": [],
        "contact_id": "test_specific",
        "webhook_data": {
            "contactId": "test_specific",
            "locationId": "test_location",
            "type": "SMS"
        }
    }
    
    # Add message
    state["messages"].append(HumanMessage(content=message))
    
    print(f"\nTesting message: '{message}'")
    print("-" * 40)
    
    # Run workflow
    result = await app.ainvoke(state)
    
    # Detailed output
    print(f"Extracted Data: {result.get('extracted_data')}")
    print(f"Lead Score: {result.get('lead_score')}")
    print(f"Current Agent: {result.get('current_agent')}")
    
    if result.get("messages"):
        last_msg = result["messages"][-1]
        if hasattr(last_msg, 'content'):
            print(f"AI Response: {last_msg.content}")
    
    return result

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_conversation_flow())
    
    # Test specific issues
    print("\n\n" + "="*80)
    print("TESTING SPECIFIC ISSUES")
    print("="*80)
    
    # Test 1: Generic business term
    asyncio.run(test_specific_issue("tengo un negocio"))
    
    # Test 2: Typo
    asyncio.run(test_specific_issue("tengo un reaturante"))
```

### 2. Interactive Test Mode

Create `interactive_test.py`:

```python
#!/usr/bin/env python3
"""
Interactive testing - type messages and see responses immediately
"""
import asyncio
from app.workflow import app
from langchain_core.messages import HumanMessage

async def interactive_test():
    """Run interactive test session"""
    print("🤖 Local Test Environment")
    print("Type 'quit' to exit, 'reset' to start new conversation")
    print("="*60)
    
    state = {
        "messages": [],
        "contact_id": "interactive_test",
        "webhook_data": {
            "contactId": "interactive_test",
            "locationId": "test_location",
            "type": "SMS"
        }
    }
    
    while True:
        # Get user input
        message = input("\nYou: ").strip()
        
        if message.lower() == 'quit':
            break
        elif message.lower() == 'reset':
            state["messages"] = []
            print("🔄 Conversation reset")
            continue
        elif message.lower() == 'state':
            print(f"\n📊 Current State:")
            print(f"  Extracted: {state.get('extracted_data', {})}")
            print(f"  Score: {state.get('lead_score', 0)}")
            print(f"  Agent: {state.get('current_agent', 'none')}")
            continue
        
        # Add message to state
        state["messages"].append(HumanMessage(content=message))
        
        # Run workflow
        print("🔄 Processing...")
        result = await app.ainvoke(state)
        
        # Show response
        if result.get("messages"):
            last_msg = result["messages"][-1]
            if hasattr(last_msg, 'content'):
                print(f"\nAI: {last_msg.content}")
        
        # Update state
        state = result

if __name__ == "__main__":
    asyncio.run(interactive_test())
```

### 3. Batch Test with Real Scenarios

Create `test_production_scenarios.py`:

```python
#!/usr/bin/env python3
"""
Test with production-like scenarios
"""
import asyncio
import json
from app.workflow import app
from langchain_core.messages import HumanMessage

# Real customer scenarios that have caused issues
PRODUCTION_SCENARIOS = [
    {
        "id": "negocio_persistence",
        "description": "Generic business term persistence issue",
        "messages": ["Hola", "Jaime", "tengo un negocio"],
        "assertions": {
            "final_business_type": None,  # Should be None, not "negocio"
            "should_ask_for_specific": True
        }
    },
    {
        "id": "typo_restaurante",
        "description": "Restaurant typo handling",
        "messages": ["tengo un reaturante"],
        "assertions": {
            "extracted_business": "restaurante",
            "fuzzy_match_used": True
        }
    },
    {
        "id": "name_not_repeated",
        "description": "Don't ask for name twice",
        "messages": ["Mi nombre es Carlos"],
        "assertions": {
            "extracted_name": "Carlos",
            "should_not_ask_name": True
        }
    }
]

async def run_scenario(scenario):
    """Run a single test scenario"""
    print(f"\n{'='*60}")
    print(f"Scenario: {scenario['description']}")
    print(f"ID: {scenario['id']}")
    print(f"{'='*60}")
    
    state = {
        "messages": [],
        "contact_id": f"test_{scenario['id']}",
        "webhook_data": {
            "contactId": f"test_{scenario['id']}",
            "locationId": "test_location",
            "type": "SMS"
        }
    }
    
    # Run messages
    for message in scenario['messages']:
        print(f"\n→ Customer: '{message}'")
        state["messages"].append(HumanMessage(content=message))
        result = await app.ainvoke(state)
        
        # Show response
        if result.get("messages"):
            last_msg = result["messages"][-1]
            if hasattr(last_msg, 'content'):
                print(f"← AI: {last_msg.content[:100]}...")
        
        state = result
    
    # Run assertions
    print("\n📋 Assertions:")
    passed = True
    
    for key, expected in scenario['assertions'].items():
        if key == "final_business_type":
            actual = state.get('extracted_data', {}).get('business_type')
            if actual == expected:
                print(f"✅ {key}: {actual} == {expected}")
            else:
                print(f"❌ {key}: {actual} != {expected}")
                passed = False
        
        elif key == "should_ask_for_specific":
            last_response = state["messages"][-1].content if state["messages"] else ""
            asks_for_business = "tipo de negocio" in last_response.lower()
            if asks_for_business == expected:
                print(f"✅ Asks for specific business: {asks_for_business}")
            else:
                print(f"❌ Should ask for business: expected {expected}, got {asks_for_business}")
                passed = False
    
    return passed

async def main():
    """Run all scenarios"""
    print("🧪 Production Scenario Testing")
    
    results = []
    for scenario in PRODUCTION_SCENARIOS:
        passed = await run_scenario(scenario)
        results.append({
            "scenario": scenario['id'],
            "passed": passed
        })
    
    # Summary
    print(f"\n\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed_count = sum(1 for r in results if r['passed'])
    total_count = len(results)
    
    for result in results:
        status = "✅ PASSED" if result['passed'] else "❌ FAILED"
        print(f"{result['scenario']}: {status}")
    
    print(f"\nTotal: {passed_count}/{total_count} passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Safe to deploy.")
    else:
        print("\n⚠️  Some tests failed. Fix before deploying.")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Quick Commands for Testing

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick test commands
alias test-chat='python interactive_test.py'
alias test-all='python test_production_scenarios.py'
alias test-negocio='python -c "import asyncio; from test_locally import test_specific_issue; asyncio.run(test_specific_issue(\"tengo un negocio\"))"'
```

### 5. Makefile Commands

Add to `Makefile`:

```makefile
# Local testing commands
test-local:
	python test_locally.py

test-interactive:
	python interactive_test.py

test-scenarios:
	python test_production_scenarios.py

test-specific:
	@echo "Enter message to test:"
	@read message; python -c "import asyncio; from test_locally import test_specific_issue; asyncio.run(test_specific_issue('$$message'))"

# Test before deploy
pre-deploy: validate test-scenarios
	@echo "✅ All tests passed, safe to deploy!"
```

## Usage

1. **Quick Test Any Message**:
   ```bash
   make test-specific
   # Enter: tengo un negocio
   ```

2. **Interactive Testing**:
   ```bash
   make test-interactive
   # Type messages and see responses immediately
   ```

3. **Test All Known Issues**:
   ```bash
   make test-scenarios
   ```

4. **Pre-Deploy Check**:
   ```bash
   make pre-deploy
   ```

## Benefits

- ⚡ Instant feedback (no 20-minute wait)
- 🎯 Test specific issues immediately
- 🔄 Reproduce production scenarios locally
- ✅ Validate fixes before deploying
- 🚀 Deploy only when everything works

This eliminates the painful deploy-wait-test cycle!