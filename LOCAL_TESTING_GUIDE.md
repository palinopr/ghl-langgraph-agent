# LOCAL_TESTING_GUIDE.md

## 🧪 Comprehensive Local Testing Guide

This guide shows you EXACTLY how to test agents locally before deploying to production.

## 🚀 Quick Start

```bash
# Activate virtual environment
source venv_langgraph/bin/activate

# Install rich for visualization (if not installed)
pip install rich

# Run the main testing interface
python test_agent_flow.py
```

## 📋 Available Testing Tools

### 1. **test_agent_flow.py** - Visual Agent Testing
The main testing interface with rich visualizations.

```bash
python test_agent_flow.py
```

Features:
- 🎨 Beautiful colored output
- 📊 Shows lead scores, routing, and responses
- 🧪 Pre-built test suite
- 🎮 Interactive single message testing
- 🔥 Edge case testing

**Example Output:**
```
━━━ Testing Message ━━━
┌─────────────────────────┐
│ Hola, tengo un restaurante │
└─────────────────────────┘

🎯 Agent Flow Results
┌──────────────┬─────────────┐
│ 📊 Lead Score │ 3/10        │
│ 🏢 Business   │ restaurante │
│ 🤖 Agent      │ MARIA       │
│ Response      │ ¡Hola! ...  │
└──────────────┴─────────────┘
```

### 2. **trace_agent_tools.py** - Tool Usage Tracking
See exactly which tools are called and when.

```bash
python trace_agent_tools.py
```

Features:
- 🔧 Patches all tools to log calls
- 📝 Shows arguments and results
- ⏱️ Timestamps for each call
- 📊 Summary statistics

**Example Output:**
```
🔧 TOOL CALLED: get_contact_details_with_task
   Call ID: get_contact_1234567
   Timestamp: 14:30:22.145
   Args: ['test-123']
   Result: {'name': 'Juan', 'tags': ['lead']}
```

### 3. **test_all_agents.py** - Individual Agent Testing
Test each agent in isolation.

```bash
python test_all_agents.py
```

Tests:
- 🧠 Intelligence Layer (scoring & extraction)
- 🎯 Supervisor (routing logic)
- 👋 Maria (cold leads)
- 💼 Carlos (warm leads)
- 📅 Sofia (hot leads)

### 4. **langsmith_local_trace.py** - LangSmith Integration
Enable detailed tracing with LangSmith.

```bash
# Set your API key first
export LANGSMITH_API_KEY=your_key_here

python langsmith_local_trace.py
```

Features:
- 🔍 Full execution traces
- 💰 Token usage tracking
- 🎯 LLM prompt inspection
- 🛠️ Tool call details

### 5. **show_agent_routing.py** - Visual Routing Logic
Understand the routing system visually.

```bash
python show_agent_routing.py
```

Shows:
- 📊 Score → Agent mapping table
- 🔄 Complete message flow
- 🧮 Scoring logic details
- 👥 Agent personalities

## 🎯 Common Test Scenarios

### Test 1: Simple Greeting
```python
message = "Hola"
# Expected: Score 1-2, Routes to Maria
```

### Test 2: Business Owner
```python
message = "Tengo un restaurante"
# Expected: Score 3-4, Routes to Maria, Extracts "restaurante"
```

### Test 3: Qualified Lead
```python
message = "Mi nombre es Juan, tengo una barbería y necesito más clientes"
# Expected: Score 5-7, Routes to Carlos
```

### Test 4: Ready to Buy
```python
message = "Quiero agendar una cita, mi presupuesto es $500"
# Expected: Score 8-10, Routes to Sofia
```

## 🔧 Quick Test Commands

### One-liner tests:
```bash
# Test Maria routing
python -c "import asyncio; from test_agent_flow import test_agent_conversation; asyncio.run(test_agent_conversation('Hola'))"

# Test business extraction
python -c "import asyncio; from test_agent_flow import test_agent_conversation; asyncio.run(test_agent_conversation('Tengo un restaurante'))"

# Test Sofia routing
python -c "import asyncio; from test_agent_flow import test_agent_conversation; asyncio.run(test_agent_conversation('Quiero agendar, presupuesto $500'))"
```

## 🐛 Debugging Tips

### 1. Enable Debug Logging
```python
import os
os.environ["LOG_LEVEL"] = "DEBUG"
```

### 2. Check State at Each Step
```python
# Add to any test script
print(f"State before: {state}")
result = await workflow.ainvoke(state)
print(f"State after: {result}")
```

### 3. Test Specific Components
```python
# Test just the intelligence layer
from app.intelligence.analyzer import IntelligenceAnalyzer
analyzer = IntelligenceAnalyzer()
result = await analyzer.analyze({"messages": [HumanMessage(content="test")]})
print(result)
```

### 4. Mock External Services
```python
# Mock GHL client for offline testing
from unittest.mock import Mock
mock_ghl = Mock()
mock_ghl.get_contact.return_value = {"name": "Test User"}
```

## 📊 Understanding Results

### Lead Scores
- **1-4**: Cold lead → Maria
- **5-7**: Warm lead → Carlos  
- **8-10**: Hot lead → Sofia

### Extracted Data
- **name**: Customer's name
- **business_type**: Type of business
- **budget**: Budget amount
- **goal**: What they want to achieve

### Tools Used
- **get_contact_details**: Load contact from GHL
- **update_contact**: Save data to GHL
- **book_appointment**: Create calendar appointment
- **escalate_to_supervisor**: Hand off to another agent

## 🚦 Pre-Deployment Checklist

Before deploying, ensure:

- [ ] All test cases pass in `test_agent_flow.py`
- [ ] No errors in edge case testing
- [ ] Tool calls work correctly (check with `trace_agent_tools.py`)
- [ ] Each agent responds appropriately (verify with `test_all_agents.py`)
- [ ] LangSmith traces show no errors
- [ ] `make validate` passes

## 💡 Pro Tips

1. **Test with Spanish typos**: "ola tngo un retaurante"
2. **Test empty messages**: See how agents handle ""
3. **Test with emojis**: "Tengo una 🍕 pizzería"
4. **Test long messages**: Paste a paragraph
5. **Test appointment booking**: "Quiero agendar para mañana a las 3pm"

## 🎮 Interactive Testing Session

For a full interactive session:
```bash
# 1. Start with routing visualization
python show_agent_routing.py

# 2. Run the test suite
python test_agent_flow.py
# Select option 1 for full suite

# 3. Test specific scenarios
python test_agent_flow.py
# Select option 2 for custom messages

# 4. Check tool usage
python trace_agent_tools.py

# 5. Enable LangSmith for deep inspection
python langsmith_local_trace.py
```

## 🔍 What to Look For

### ✅ Good Signs:
- Correct agent routing based on score
- Spanish text extracted properly
- Natural, contextual responses
- Tools called appropriately
- No errors in traces

### ❌ Red Flags:
- Wrong agent selected
- Missing data extraction
- English responses to Spanish
- Tools not being called
- Errors or exceptions

## 📝 Example Test Session

```bash
$ python test_agent_flow.py

🤖 Agent Testing System
========================
1. Run full test suite
2. Test single message
3. Test edge cases
4. Exit

Select option: 1

TEST CASE 1/5
Expected: Should go to Maria (score 1-4)

━━━ Testing Message ━━━
┌──────┐
│ Hola │
└──────┘

🎯 Agent Flow Results
┌─────────────────┬──────────────┐
│ 📊 Lead Score   │ 1/10         │
│ 🏢 Business Type│ Not detected │
│ 🤖 Assigned Agent│ MARIA       │
└─────────────────┴──────────────┘

Agent Response:
┌─────────────────────────────────────┐
│ ¡Hola! Soy María de WhatsApp       │
│ Automation. ¿Me podrías compartir   │
│ tu nombre?                          │
└─────────────────────────────────────┘
```

Now you have everything needed to thoroughly test agents locally! 🎉