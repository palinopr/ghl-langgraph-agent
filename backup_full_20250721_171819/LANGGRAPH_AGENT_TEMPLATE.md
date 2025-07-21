# LangGraph Multi-Agent System Template Guide

## 🚀 Quick Start - Building Your Own Agent System

This guide shows you how to build a production-ready multi-agent system like the GHL WhatsApp automation project. Follow this template to create your own specialized agents.

## 📋 Table of Contents
1. [Project Structure](#project-structure)
2. [Core Components](#core-components)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Agent Templates](#agent-templates)
5. [Workflow Patterns](#workflow-patterns)
6. [Best Practices](#best-practices)
7. [Testing & Debugging](#testing--debugging)
8. [Deployment](#deployment)

## 🏗️ Project Structure

Create this structure for your project:

```
your-project/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── receptionist_agent.py    # Data gatherer
│   │   ├── supervisor_agent.py      # Router/orchestrator
│   │   ├── specialist_agent_1.py    # Your domain expert
│   │   ├── specialist_agent_2.py    # Another expert
│   │   └── responder_agent.py       # Message sender
│   ├── state/
│   │   └── conversation_state.py    # Shared state schema
│   ├── tools/
│   │   ├── agent_tools.py          # Agent-specific tools
│   │   └── api_client.py           # External API integrations
│   ├── utils/
│   │   ├── conversation_enforcer.py # Conversation rules
│   │   ├── simple_logger.py        # Logging
│   │   └── model_factory.py        # LLM configuration
│   ├── workflow.py                  # Main workflow definition
│   └── config.py                    # Configuration
├── tests/
├── requirements.txt
├── .env.example
├── langgraph.json                   # LangGraph deployment config
└── README.md
```

## 🔧 Core Components

### 1. State Management (conversation_state.py)

```python
from typing import List, Optional, Dict, Any
from langgraph.graph import add_messages
from pydantic import BaseModel, Field

class ConversationState(BaseModel):
    """Shared state for all agents"""
    # Core fields
    messages: List[Any] = Field(default_factory=list)
    contact_id: str
    
    # Routing
    current_agent: Optional[str] = None
    next_agent: Optional[str] = None
    routing_attempts: int = 0
    
    # Data collection
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    lead_score: int = 0
    
    # Control flags
    should_end: bool = False
    needs_rerouting: bool = False
    escalation_reason: Optional[str] = None
    
    # External data
    webhook_data: Optional[Dict[str, Any]] = None
    
    class Config:
        arbitrary_types_allowed = True
```

### 2. Supervisor Pattern (supervisor_agent.py)

```python
"""
Supervisor - The Brain That Routes Messages
"""
from typing import Dict, Any, Literal
from langchain_core.messages import AIMessage
from app.state.conversation_state import ConversationState
from app.utils.simple_logger import get_logger

logger = get_logger("supervisor")

async def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze and route to appropriate agent
    """
    try:
        # Extract current message
        messages = state.get("messages", [])
        current_message = messages[-1].content if messages else ""
        
        # Analyze intent/score/context
        analysis = analyze_message(current_message, state)
        
        # Determine routing
        if analysis["score"] >= 8:
            next_agent = "specialist_high"
        elif analysis["score"] >= 5:
            next_agent = "specialist_medium"
        else:
            next_agent = "specialist_low"
        
        logger.info(f"Routing to {next_agent} (score: {analysis['score']})")
        
        return {
            "next_agent": next_agent,
            "lead_score": analysis["score"],
            "extracted_data": analysis["data"]
        }
        
    except Exception as e:
        logger.error(f"Supervisor error: {e}")
        return {"next_agent": "specialist_low", "error": str(e)}

def analyze_message(message: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Your custom analysis logic"""
    # Implement your scoring/extraction logic
    return {
        "score": calculate_score(message, state),
        "data": extract_data(message)
    }
```

### 3. Specialist Agent Template (specialist_agent.py)

```python
"""
Specialist Agent Template - Customize for Your Domain
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools import your_custom_tools
from app.utils.model_factory import create_openai_model

class SpecialistState(AgentState):
    """Extended state for specialist"""
    contact_id: str
    lead_score: int
    extracted_data: Optional[Dict[str, Any]]

def specialist_prompt(state: SpecialistState) -> list[AnyMessage]:
    """
    Dynamic prompt based on state
    """
    extracted_data = state.get("extracted_data", {})
    
    system_prompt = f"""You are a specialist in [YOUR DOMAIN].
    
Current Context:
- Lead Score: {state.get('lead_score', 0)}
- Known Data: {extracted_data}

Your Goals:
1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

Communication Style:
- Be professional yet friendly
- Keep responses concise
- Focus on value

Available Tools:
- tool1: Description
- tool2: Description

Remember: [Key rules for your use case]
"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]

def create_specialist_agent():
    """Create the specialist agent"""
    model = create_openai_model(temperature=0.7)
    
    agent = create_react_agent(
        model=model,
        tools=your_custom_tools,
        state_schema=SpecialistState,
        prompt=specialist_prompt,
        name="specialist"
    )
    
    return agent

async def specialist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node wrapper for workflow"""
    agent = create_specialist_agent()
    result = await agent.ainvoke(state)
    
    return {
        "messages": result.get("messages", []),
        "current_agent": "specialist"
    }
```

### 4. Workflow Definition (workflow.py)

```python
"""
Main Workflow - Connects All Agents
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.state.conversation_state import ConversationState
from app.agents import (
    receptionist_node,
    supervisor_node,
    specialist_1_node,
    specialist_2_node,
    responder_node
)

def create_workflow():
    """Create the multi-agent workflow"""
    # Initialize graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("receptionist", receptionist_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("specialist_1", specialist_1_node)
    workflow.add_node("specialist_2", specialist_2_node)
    workflow.add_node("responder", responder_node)
    
    # Define edges
    workflow.set_entry_point("receptionist")
    workflow.add_edge("receptionist", "supervisor")
    
    # Conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "specialist_1": "specialist_1",
            "specialist_2": "specialist_2",
            "end": END
        }
    )
    
    # All specialists go to responder
    workflow.add_edge("specialist_1", "responder")
    workflow.add_edge("specialist_2", "responder")
    workflow.add_edge("responder", END)
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

def route_from_supervisor(state: ConversationState) -> str:
    """Routing logic"""
    if state.get("should_end"):
        return "end"
    return state.get("next_agent", "specialist_1")

# Create the workflow
workflow = create_workflow()
```

## 📝 Step-by-Step Implementation

### Step 1: Define Your Use Case

1. **Identify your agents:**
   - What specialists do you need?
   - What should each agent handle?
   - How do they hand off work?

2. **Define your scoring/routing logic:**
   - What makes a "high priority" case?
   - What data needs to be extracted?
   - What are the routing rules?

### Step 2: Create Your State Schema

```python
# Extend ConversationState for your needs
class YourProjectState(ConversationState):
    # Add your custom fields
    customer_type: Optional[str] = None
    priority_level: int = 0
    custom_data: Dict[str, Any] = Field(default_factory=dict)
```

### Step 3: Build Your Agents

1. **Start with templates** (copy from above)
2. **Customize prompts** for your domain
3. **Add specific tools** each agent needs
4. **Define handoff conditions**

### Step 4: Implement Conversation Rules

```python
# conversation_enforcer.py
class ConversationEnforcer:
    """Enforce your conversation flow"""
    
    STAGES = {
        "greeting": "Hi! I'm here to help with [YOUR SERVICE]. What's your name?",
        "collect_info": "Great, {name}. Tell me about [YOUR TOPIC].",
        "qualification": "I understand. Let me ask you about [QUALIFICATION].",
        # Add your stages
    }
    
    def get_next_response(self, stage: str, data: dict) -> str:
        """Get the appropriate response for current stage"""
        template = self.STAGES.get(stage, "")
        return template.format(**data)
```

### Step 5: Add Your Tools

```python
from langchain_core.tools import tool

@tool
def check_availability(date: str, service: str) -> str:
    """Check availability for a service"""
    # Your implementation
    return f"Available slots for {service} on {date}: ..."

@tool
def create_booking(customer_id: str, service: str, datetime: str) -> str:
    """Create a booking"""
    # Your implementation
    return f"Booking created: {booking_id}"

# Export your tools
your_custom_tools = [
    check_availability,
    create_booking
]
```

## 🎯 Workflow Patterns

### Pattern 1: Linear Flow (Recommended)
```
Start → Receptionist → Supervisor → Agent → Responder → End
```

### Pattern 2: Escalation Pattern
```python
# In your agent
if complex_case:
    return {
        "needs_rerouting": True,
        "escalation_reason": "needs_expert",
        "current_agent": "basic_agent"
    }
```

### Pattern 3: Conditional Routing
```python
def route_logic(state):
    score = state.get("lead_score", 0)
    
    if score >= 8 and state.get("has_budget"):
        return "closing_agent"
    elif score >= 5:
        return "nurture_agent"
    else:
        return "info_agent"
```

## ✅ Best Practices

### 1. State Management
- Keep state minimal - only what's needed
- Use `extracted_data` dict for flexible storage
- Always update `current_agent` in nodes

### 2. Error Handling
```python
try:
    # Your agent logic
    result = await agent.ainvoke(state)
except Exception as e:
    logger.error(f"Agent error: {e}")
    return {
        "error": str(e),
        "needs_rerouting": True,
        "escalation_reason": "error"
    }
```

### 3. Logging
```python
from app.utils.simple_logger import get_logger

logger = get_logger("agent_name")
logger.info(f"Processing message: {message[:50]}...")
logger.error(f"Failed to process: {error}")
```

### 4. Testing Strategy
```python
# test_workflow.py
async def test_full_flow():
    initial_state = {
        "messages": [HumanMessage(content="Test message")],
        "contact_id": "test123",
        "webhook_data": {"source": "test"}
    }
    
    result = await workflow.ainvoke(initial_state)
    assert result["current_agent"] == "expected_agent"
```

## 🐛 Testing & Debugging

### 1. Local Testing
```bash
# Create test script
python test_local.py

# With specific message
python test_local.py "Your test message here"
```

### 2. Trace Analysis
```python
# Enable LangSmith tracing
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-key"
os.environ["LANGCHAIN_PROJECT"] = "your-project"
```

### 3. Common Issues & Solutions

**Issue**: Agent not responding correctly
```python
# Add debug logging
logger.info(f"State before: {state}")
result = await agent.ainvoke(state)
logger.info(f"State after: {result}")
```

**Issue**: Routing loops
```python
# Add routing counter
if state.get("routing_attempts", 0) > 2:
    return {"should_end": True}
```

## 🚀 Deployment

### 1. Environment Variables (.env)
```bash
# LLM Configuration
OPENAI_API_KEY=sk-...

# Your API Keys
YOUR_API_KEY=...

# LangSmith (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=your-project-name
```

### 2. LangGraph Configuration (langgraph.json)
```json
{
  "python_version": "3.11",
  "dependencies": ["."],
  "graphs": {
    "agent": {
      "module": "app.workflow",
      "class": "workflow"
    }
  },
  "env": ".env"
}
```

### 3. Requirements (requirements.txt)
```
langgraph>=0.3.27
langchain>=0.3.8
langchain-openai>=0.1.7
pydantic>=2.0.0
python-dotenv>=1.0.0
httpx>=0.24.0
```

### 4. Deployment Commands
```bash
# Validate before deployment
python validate_workflow.py

# Deploy to LangGraph Cloud
git add .
git commit -m "Deploy agent system"
git push origin main
```

## 🎓 Learning Path

1. **Start Simple**: One supervisor + one agent
2. **Add Complexity**: Multiple agents with different roles  
3. **Add Intelligence**: Scoring, extraction, routing
4. **Add Rules**: Conversation enforcement
5. **Add Features**: Tools, APIs, integrations
6. **Optimize**: Performance, error handling
7. **Deploy**: Production-ready system

## 📚 Resources

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools](https://python.langchain.com/docs/modules/tools)
- [Deployment Guide](https://langchain-ai.github.io/langgraph/deployment/)

## 🚨 Important Tips

1. **Always validate before deploying** - Saves 15 minutes per failed deployment
2. **Use escalation, not direct transfers** - Prevents circular loops
3. **Log everything during development** - Makes debugging easier
4. **Test with real data** - Mock data hides issues
5. **Keep agents focused** - Each agent should do one thing well

---

## Quick Start Checklist

- [ ] Copy this template structure
- [ ] Define your agents and their roles
- [ ] Create your state schema
- [ ] Implement supervisor routing logic
- [ ] Build your specialist agents
- [ ] Add necessary tools
- [ ] Create workflow connections
- [ ] Test locally
- [ ] Add error handling
- [ ] Deploy to LangGraph Cloud

This template is based on production experience building the GHL WhatsApp automation system. Customize it for your specific needs!