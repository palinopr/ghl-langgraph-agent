# AGENT_DUPLICATION.md

## 🔍 Agent Duplication Analysis

### Files Analyzed
1. `maria_memory_aware.py` - 149 lines
2. `carlos_agent_v2_fixed.py` - 155 lines  
3. `sofia_agent_v2_fixed.py` - 193 lines
**Total: 497 lines across 3 agents**

## 📊 Duplication Found

### 1. Common Imports (100% Identical)
```python
# ALL THREE have these imports
from typing import Dict, Any, List, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
```

### 2. Common Patterns

#### A. Agent Node Structure (90% Identical)
All three agents follow this exact pattern:
```python
async def [agent]_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # 1. Check lead score boundaries
        lead_score = state.get("lead_score", 0)
        if [score out of range]:
            return escalation_response
        
        # 2. Create agent
        agent = create_[agent]_agent()
        result = await agent.ainvoke(state)
        
        # 3. Return updated state
        return {
            "messages": result.get("messages", []),
            "current_agent": "[agent_name]"
        }
    except Exception as e:
        logger.error(f"[Agent] error: {str(e)}")
        return error_response
```

#### B. Agent Creation Pattern (85% Identical)
```python
def create_[agent]_agent():
    model = create_openai_model(temperature=0.3)  # Same temp!
    tools = [same 4 tools mostly]
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=[AgentState],
        prompt=[agent]_prompt,
        name="[agent]"
    )
    return agent
```

#### C. State Analysis Pattern (80% Similar)
All agents:
- Extract `contact_id`, `lead_score`, `extracted_data`
- Check what data is collected (name, business, budget, email)
- Calculate next step based on missing data
- Format context for prompt

#### D. Error Handling (100% Identical)
```python
except Exception as e:
    logger.error(f"[Agent] error: {str(e)}", exc_info=True)
    return {
        "error": str(e),
        "current_agent": "[agent]"
    }
```

### 3. Common Tool Usage
All three agents use these tools:
- `get_contact_details_with_task` 
- `update_contact_with_context`
- `escalate_to_supervisor`
- `save_important_context` (Maria/Carlos only)
- `book_appointment_with_instructions` (Sofia only)

### 4. Duplicate Logic Patterns

#### Score Range Checking (100% Duplicate)
```python
# Maria
if lead_score >= 5:
    return escalation

# Carlos  
if lead_score < 5:
    return escalation
elif lead_score >= 8:
    return escalation

# Sofia
if lead_score < 8:
    return escalation
```

#### Data Collection Logic (90% Duplicate)
```python
# All agents check:
has_name = bool(extracted_data.get("name"))
has_business = bool(extracted_data.get("business_type"))
has_budget = bool(extracted_data.get("budget"))
has_email = bool(extracted_data.get("email"))
```

#### Message Extraction (100% Duplicate)
```python
# Get current message from state
messages = state.get("messages", [])
current_message = messages[-1].content if messages else ""
```

## 🎯 What's Actually Different?

### 1. Agent-Specific Differences
- **Maria**: 
  - Score range: 0-4
  - Focus: Initial contact, trust building
  - Special: Memory isolation context
  
- **Carlos**: 
  - Score range: 5-7
  - Focus: Qualification, WhatsApp benefits
  - Special: Template enforcement
  
- **Sofia**: 
  - Score range: 8-10
  - Focus: Appointment booking
  - Special: Strict order enforcement, calendar tools

### 2. Prompt Content (The Main Difference!)
Each agent has unique:
- Personality description
- Conversation flow rules
- Response templates
- Escalation conditions

### 3. State Schema
- Maria: Uses basic Dict[str, Any]
- Carlos: Has CarlosState with specific fields
- Sofia: Has SofiaState with appointment fields

## 💡 Proposed Base Agent Class

```python
# app/agents/base_agent.py
class BaseSpanishAgent:
    def __init__(self, 
                 name: str,
                 personality: str,
                 focus: str,
                 score_range: Tuple[int, int],
                 temperature: float = 0.3):
        self.name = name
        self.personality = personality  
        self.focus = focus
        self.score_range = score_range
        self.temperature = temperature
        self.logger = get_logger(f"{name}_agent")
        
    def check_score_boundaries(self, lead_score: int) -> Optional[Dict]:
        """Common score boundary checking"""
        min_score, max_score = self.score_range
        if lead_score < min_score or lead_score > max_score:
            return {
                "needs_rerouting": True,
                "escalation_reason": "wrong_score_range",
                "current_agent": self.name
            }
        return None
        
    def extract_conversation_data(self, state: Dict) -> Dict:
        """Common data extraction logic"""
        extracted = state.get("extracted_data", {})
        return {
            "has_name": bool(extracted.get("name")),
            "has_business": bool(extracted.get("business_type")),
            "has_budget": bool(extracted.get("budget")),
            "has_email": bool(extracted.get("email")),
            "current_message": self.get_current_message(state),
            "lead_score": state.get("lead_score", 0)
        }
        
    def get_current_message(self, state: Dict) -> str:
        """Extract current message from state"""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
                return msg.content
        return ""
        
    def create_base_prompt(self, context: Dict) -> str:
        """Base prompt structure all agents share"""
        return f"""You are {self.name}, {self.personality} for Main Outlet Media.
        
CURRENT STATUS:
- Lead Score: {context['lead_score']}/10
- Has Name: {'✅' if context['has_name'] else '❌'}
- Has Business: {'✅' if context['has_business'] else '❌'}
- Has Budget: {'✅' if context['has_budget'] else '❌'}
- Has Email: {'✅' if context['has_email'] else '❌'}

YOUR FOCUS: {self.focus}
YOUR SCORE RANGE: {self.score_range[0]}-{self.score_range[1]}

Current message: "{context['current_message']}"
"""
        
    async def process_node(self, state: Dict) -> Dict:
        """Common node processing logic"""
        try:
            # Check boundaries
            boundary_check = self.check_score_boundaries(state.get("lead_score", 0))
            if boundary_check:
                return boundary_check
                
            # Create and run agent
            agent = self.create_agent()
            result = await agent.ainvoke(state)
            
            # Return standard response
            return {
                "messages": result.get("messages", []),
                "current_agent": self.name.lower()
            }
            
        except Exception as e:
            self.logger.error(f"{self.name} error: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "current_agent": self.name.lower()
            }
```

## 📈 Consolidation Opportunities

### 1. Immediate Wins (Low Risk)
- Extract common imports to base class
- Consolidate error handling 
- Unify score boundary checking
- Share data extraction logic
- **Estimated savings: 150+ lines (30%)**

### 2. Medium Effort (Medium Risk)
- Create base node processor
- Unify agent creation pattern
- Share message extraction
- Common state analysis
- **Estimated savings: 200+ lines (40%)**

### 3. Full Refactor (Higher Risk)
- Complete base class implementation
- Agent-specific classes inherit
- Prompt templates in config
- Dynamic tool assignment
- **Estimated savings: 300+ lines (60%)**

## 🚨 Risk Assessment

### Low Risk Items
- ✅ Common imports - Zero functional impact
- ✅ Error handling - Already identical
- ✅ Score checking - Simple logic
- ✅ Message extraction - Pure utility

### Medium Risk Items  
- ⚠️ State handling - Different schemas per agent
- ⚠️ Prompt generation - Core agent behavior
- ⚠️ Tool selection - Sofia has unique tools

### High Risk Items
- ❌ Complete consolidation - May reduce flexibility
- ❌ Dynamic prompts - Could affect agent personality
- ❌ Unified state - Breaking change

## 🎯 Recommendation

Start with **Low Risk** consolidation:
1. Create `BaseSpanishAgent` with common utilities
2. Extract shared patterns (imports, errors, score checks)
3. Keep agent-specific prompts and logic separate
4. Test thoroughly before proceeding

**Expected impact**: 
- 30-40% code reduction
- Easier maintenance
- Consistent behavior
- Preserved agent personalities

The agents share significant structural code but have important behavioral differences in their prompts and conversation flows. A base class can eliminate the structural duplication while preserving the unique agent personalities.