# Quick Start Example - Customer Support Bot

Let's build a simple customer support bot with 3 agents in 30 minutes!

## What We're Building
- **Receptionist**: Greets and collects basic info
- **Support Agent**: Handles general questions
- **Escalation Agent**: Handles complex issues
- **Responder**: Sends the response

## Step 1: Create Project Structure (2 minutes)

```bash
mkdir customer-support-bot
cd customer-support-bot
mkdir -p app/agents app/state app/tools app/utils
touch app/__init__.py app/agents/__init__.py
```

## Step 2: Create State (3 minutes)

```python
# app/state/support_state.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SupportState(BaseModel):
    """State for customer support workflow"""
    messages: List[Any] = Field(default_factory=list)
    customer_id: str
    customer_name: Optional[str] = None
    issue_type: Optional[str] = None  # billing, technical, general
    priority: int = 1  # 1-5 scale
    resolved: bool = False
    next_agent: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
```

## Step 3: Create Simple Logger (2 minutes)

```python
# app/utils/logger.py
import logging

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
```

## Step 4: Create Receptionist (5 minutes)

```python
# app/agents/receptionist.py
from typing import Dict, Any
from app.state.support_state import SupportState
from app.utils.logger import get_logger

logger = get_logger("receptionist")

async def receptionist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Greet customer and determine issue type
    """
    messages = state.get("messages", [])
    
    # If this is first message
    if len(messages) <= 1:
        greeting = "Hello! I'm here to help. What's your name?"
        return {
            "messages": messages + [{"role": "assistant", "content": greeting}],
            "next_agent": "receptionist"  # Stay here for name
        }
    
    # Get last message
    last_message = messages[-1].get("content", "").lower()
    
    # Extract name if we don't have it
    if not state.get("customer_name"):
        # Simple name extraction (you'd improve this)
        name = last_message.split()[0].title()
        
        followup = f"Nice to meet you, {name}! What can I help you with today?"
        return {
            "messages": messages + [{"role": "assistant", "content": followup}],
            "customer_name": name,
            "next_agent": "supervisor"
        }
    
    return {"next_agent": "supervisor"}
```

## Step 5: Create Supervisor (5 minutes)

```python
# app/agents/supervisor.py
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("supervisor")

async def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route to appropriate agent based on issue
    """
    messages = state.get("messages", [])
    last_message = messages[-1].get("content", "").lower()
    
    # Simple keyword-based routing
    if any(word in last_message for word in ["bill", "payment", "charge", "refund"]):
        issue_type = "billing"
        priority = 3
        next_agent = "support"
    elif any(word in last_message for word in ["broken", "error", "crash", "bug"]):
        issue_type = "technical"
        priority = 4
        next_agent = "escalation"
    else:
        issue_type = "general"
        priority = 2
        next_agent = "support"
    
    logger.info(f"Routing to {next_agent} for {issue_type} issue (priority: {priority})")
    
    return {
        "issue_type": issue_type,
        "priority": priority,
        "next_agent": next_agent
    }
```

## Step 6: Create Support Agent (5 minutes)

```python
# app/agents/support_agent.py
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("support")

async def support_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle general support questions
    """
    issue_type = state.get("issue_type", "general")
    customer_name = state.get("customer_name", "there")
    
    responses = {
        "billing": f"I understand you have a billing question, {customer_name}. Let me help you with that. Can you provide your account number?",
        "general": f"I'd be happy to help you with that, {customer_name}. Can you tell me more about what you're experiencing?",
        "technical": f"I see you're having technical issues, {customer_name}. Let me get someone who can better assist you."
    }
    
    response = responses.get(issue_type, "I'm here to help. Can you tell me more?")
    
    # For technical issues, escalate
    if issue_type == "technical":
        next_agent = "escalation"
    else:
        next_agent = "responder"
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": response}],
        "next_agent": next_agent
    }
```

## Step 7: Create Escalation Agent (3 minutes)

```python
# app/agents/escalation_agent.py
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("escalation")

async def escalation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle complex issues that need escalation
    """
    customer_name = state.get("customer_name", "")
    issue_type = state.get("issue_type", "")
    
    response = (
        f"I understand this is urgent, {customer_name}. "
        f"I'm creating a high-priority ticket for your {issue_type} issue. "
        "A specialist will contact you within 2 hours. "
        "Your ticket number is #12345."
    )
    
    return {
        "messages": state["messages"] + [{"role": "assistant", "content": response}],
        "resolved": True,
        "next_agent": "responder"
    }
```

## Step 8: Create Responder (2 minutes)

```python
# app/agents/responder.py
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("responder")

async def responder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send the final response
    """
    messages = state.get("messages", [])
    
    # Get last assistant message
    last_response = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            last_response = msg.get("content")
            break
    
    if last_response:
        logger.info(f"Sending response: {last_response[:50]}...")
        # Here you would actually send the message
        # await send_message(state["customer_id"], last_response)
    
    return {"response_sent": True}
```

## Step 9: Create Workflow (5 minutes)

```python
# app/workflow.py
from langgraph.graph import StateGraph, END
from app.state.support_state import SupportState
from app.agents.receptionist import receptionist_node
from app.agents.supervisor import supervisor_node
from app.agents.support_agent import support_node
from app.agents.escalation_agent import escalation_node
from app.agents.responder import responder_node

def create_workflow():
    """Create the support workflow"""
    workflow = StateGraph(SupportState)
    
    # Add all nodes
    workflow.add_node("receptionist", receptionist_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("support", support_node)
    workflow.add_node("escalation", escalation_node)
    workflow.add_node("responder", responder_node)
    
    # Entry point
    workflow.set_entry_point("receptionist")
    
    # Define edges
    workflow.add_conditional_edges(
        "receptionist",
        lambda x: x.get("next_agent", "supervisor"),
        {
            "receptionist": "receptionist",
            "supervisor": "supervisor"
        }
    )
    
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x.get("next_agent", "support"),
        {
            "support": "support",
            "escalation": "escalation"
        }
    )
    
    workflow.add_conditional_edges(
        "support",
        lambda x: x.get("next_agent", "responder"),
        {
            "responder": "responder",
            "escalation": "escalation"
        }
    )
    
    workflow.add_edge("escalation", "responder")
    workflow.add_edge("responder", END)
    
    return workflow.compile()

# Create the workflow
workflow = create_workflow()
```

## Step 10: Test It! (2 minutes)

```python
# test_bot.py
import asyncio
from app.workflow import workflow

async def test_conversation():
    # Test 1: General inquiry
    print("=== TEST 1: General Inquiry ===")
    result = await workflow.ainvoke({
        "messages": [{"role": "user", "content": "Hi"}],
        "customer_id": "test123"
    })
    print(f"Final state: {result}")
    
    # Test 2: Billing issue
    print("\n=== TEST 2: Billing Issue ===")
    result = await workflow.ainvoke({
        "messages": [{"role": "user", "content": "I have a problem with my bill"}],
        "customer_id": "test456"
    })
    print(f"Final state: {result}")
    
    # Test 3: Technical issue (escalation)
    print("\n=== TEST 3: Technical Issue ===")
    result = await workflow.ainvoke({
        "messages": [{"role": "user", "content": "The app keeps crashing"}],
        "customer_id": "test789"
    })
    print(f"Final state: {result}")

if __name__ == "__main__":
    asyncio.run(test_conversation())
```

## 🎉 Done! You Have a Working Bot

### What You Built:
- ✅ Multi-agent system with proper handoffs
- ✅ Routing based on customer needs
- ✅ Escalation for complex issues
- ✅ Clean, modular architecture

### Next Steps:
1. **Add Real Tools**: Database lookups, API calls
2. **Improve NLU**: Better intent detection
3. **Add Memory**: Store conversation history
4. **Add Auth**: Verify customer identity
5. **Deploy**: Use LangGraph Cloud

### To Run:
```bash
# Install dependencies
pip install langgraph langchain pydantic

# Run tests
python test_bot.py
```

### Key Patterns Used:
1. **State Management**: Single source of truth
2. **Conditional Routing**: Based on analysis
3. **Agent Specialization**: Each agent has one job
4. **Clean Handoffs**: Clear next_agent logic

This example shows the basics. For production, add:
- Error handling
- Better NLU
- Real integrations
- Conversation rules
- Testing suite

Total time: ~30 minutes to working prototype! 🚀