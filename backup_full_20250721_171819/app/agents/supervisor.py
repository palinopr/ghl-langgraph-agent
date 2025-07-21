"""
Supervisor Agent - Orchestrates routing between agents
Using latest LangGraph patterns with create_react_agent
"""
from typing import Literal, Dict, Any
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langgraph.graph import MessagesState, END
from app.tools.agent_tools_v2 import supervisor_tools
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result

logger = get_logger("supervisor")


from typing import Optional
from app.state.conversation_state import ConversationState

class SupervisorState(ConversationState):
    """State for supervisor extending ConversationState to access all fields"""
    pass  # ConversationState already has all required fields including remaining_steps


def supervisor_prompt(state: SupervisorState) -> list[AnyMessage]:
    """
    Dynamic prompt for the supervisor based on current state
    """
    current = state.get("current_agent", "none")
    lead_score = state.get("lead_score", 0)
    score_reasoning = state.get("score_reasoning", "No scoring available")
    suggested_agent = state.get("suggested_agent", None)
    lead_category = state.get("lead_category", "unknown")
    
    # Build context about extracted information AND qualification status
    extracted = state.get("extracted_data", {})
    context_info = []
    if extracted.get("name"):
        context_info.append(f"Name: {extracted['name']} ✓")
    if extracted.get("business_type"):
        context_info.append(f"Business: {extracted['business_type']} ✓")
    if extracted.get("budget"):
        context_info.append(f"Budget: {extracted['budget']} {'✓ QUALIFIED' if '$300' in str(extracted['budget']) or '300' in str(extracted['budget']) else '❌ CHECK'}")
    if extracted.get("goal"):
        context_info.append(f"Goal: {extracted['goal']}")
    if extracted.get("email"):
        context_info.append(f"Email: {extracted['email']} ✓")
    
    # Qualification status
    has_email = bool(extracted.get("email"))
    has_budget_300 = bool(extracted.get("budget") and ('300' in str(extracted['budget']) or int(str(extracted.get('budget', '0')).replace('$', '').replace('+', '').split('/')[0] or 0) >= 300))
    has_name = bool(extracted.get("name"))
    
    context_str = "\n".join(context_info) if context_info else "No information extracted yet"
    
    qualification_str = f"""
APPOINTMENT QUALIFICATION CHECK:
• Name: {"✓ YES" if has_name else "❌ NO"}
• Email: {"✓ YES" if has_email else "❌ NO"} 
• Budget $300+: {"✓ CONFIRMED" if has_budget_300 else "❌ NOT CONFIRMED"}
• Can book appointment: {"YES - Send to Sofia" if all([has_name, has_email, has_budget_300]) else "NO - Need qualification first"}
"""
    
    system_prompt = f"""You are an intelligent routing supervisor for Main Outlet Media.
Your role is to analyze conversations and route to the appropriate specialist agent based on lead score and context.

Current Status:
- Current agent: {current}
- Lead Score: {lead_score}/10 ({lead_category})
- Score Reasoning: {score_reasoning}
- Intelligence Suggestion: Route to {suggested_agent or 'no suggestion'}

Extracted Information:
{context_str}

{qualification_str}

ROUTING RULES (QUALIFICATION-BASED):

1. **APPOINTMENT READY (Route to Sofia)**:
   - Score 6+ AND
   - Has Name AND
   - Has Email AND
   - Budget $300+ CONFIRMED
   
2. **NEEDS QUALIFICATION (Route to Carlos)**:
   - Score 5-7 OR
   - Missing budget confirmation OR
   - Has business but needs nurturing
   
3. **COLD/INFO GATHERING (Route to Maria)**:
   - Score 1-4 OR
   - Very limited information OR
   - Just starting conversation

⚠️ CRITICAL: NEVER route to Sofia without ALL qualifications!

2. **Context-Based Override Rules**:
   - If user explicitly asks for appointment → Sofia (regardless of score)
   - If user mentions specific budget amount → Carlos (to qualify)
   - If user has general questions → Maria (for support)
   - If current agent is handling well → Let them continue

3. **Special Cases**:
   - Budget confirmation ("si" after $300 mention) → Immediate route to Sofia
   - Multiple failed attempts by current agent → Escalate up (Maria→Carlos→Sofia)
   - Technical issues or complaints → Always Maria

Available agents:
1. **Sofia** - Appointment Setting Specialist (HOT LEADS)
   - Use transfer_to_sofia tool
   
2. **Carlos** - Lead Qualification Specialist (WARM LEADS)
   - Use transfer_to_carlos tool
   
3. **Maria** - Customer Support Representative (COLD LEADS)
   - Use transfer_to_maria tool

IMPORTANT INSTRUCTIONS:
- Consider the lead score as PRIMARY routing factor
- But allow context to override when user intent is clear
- You MUST use one of the transfer tools to route

⚠️ CRITICAL: You MUST use the transfer tools! Do not just suggest routing - actually USE the tool:
- For Sofia: Use transfer_to_sofia tool
- For Carlos: Use transfer_to_carlos tool  
- For Maria: Use transfer_to_maria tool

Analyze the situation and then IMMEDIATELY use the appropriate transfer tool.
- Include reasoning when transferring (e.g., "Transferring to Sofia because lead score is 8 and budget is confirmed")
- Do NOT answer questions yourself - always delegate"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_supervisor_agent():
    """Create the supervisor agent"""
    settings = get_settings()
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=supervisor_tools,
        state_schema=SupervisorState,
        prompt=supervisor_prompt,
        name="supervisor"
    )
    
    logger.info("Created supervisor agent")
    return agent


async def supervisor_node(state: Dict[str, Any]) -> Command[Literal["sofia", "carlos", "maria", "end"]]:
    """
    Supervisor node that decides routing
    Always returns a Command to route to an agent or end
    """
    try:
        # Create and invoke supervisor
        supervisor = create_supervisor_agent()
        result = await supervisor.ainvoke(state)
        
        # The supervisor should have used a transfer tool
        # which returns a Command object
        # Extract the routing decision from the result
        
        # Check if we should end the conversation
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            # Check for conversation ending signals
            if any(phrase in str(last_message).lower() for phrase in 
                   ["goodbye", "thank you for choosing", "have a great day"]):
                logger.info("Supervisor detected conversation end")
                return Command(goto=END, update=filter_agent_result(result))
        
        # Check if a transfer was made
        next_agent = result.get("next_agent")
        if next_agent:
            logger.info(f"Supervisor routing to {next_agent}")
            return Command(
                goto=next_agent,
                update={
                    "current_agent": next_agent,
                    "routing_reason": f"Routed by supervisor to {next_agent}"
                }
            )
        
        # Default routing based on analysis
        # This shouldn't happen if tools are used correctly
        logger.warning("Supervisor didn't use transfer tools, applying default routing")
        return Command(
            goto="maria",  # Default to Maria for safety
            update={
                "current_agent": "maria",
                "routing_reason": "Default routing to Maria"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in supervisor: {str(e)}", exc_info=True)
        # On error, route to Maria for support
        return Command(
            goto="maria",
            update={
                "error": str(e),
                "current_agent": "maria",
                "routing_reason": f"Error routing: {str(e)}"
            }
        )


# For backward compatibility
orchestrator_node = supervisor_node

__all__ = ["supervisor_node", "orchestrator_node", "create_supervisor_agent", "SupervisorState"]