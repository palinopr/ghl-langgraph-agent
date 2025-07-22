"""
Supervisor with proper LangGraph 0.5.3 patterns
Uses Command objects for routing instead of string parsing
"""
from typing import Dict, Any, List, Optional, Literal
from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.state.minimal_state import MinimalState
from langchain_core.tools import tool
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState

logger = get_logger("supervisor")


# Create handoff tools that return proper Command objects
@tool
def handoff_to_sofia(
    task_description: Annotated[str, "Description of what Sofia should do next"],
    state: Annotated[MinimalState, InjectedState]
) -> Command[Literal["sofia"]]:
    """
    Handoff to Sofia - Appointment Setting Specialist.
    Use when:
    - Lead score is 8-10 (hot leads)
    - Customer is ready to book appointment
    - Has name, email, and $300+ budget confirmed
    """
    logger.info(f"Handoff to Sofia with task: {task_description}")
    return Command(
        goto="sofia",
        update={
            "agent_task": task_description,
            "next_agent": "sofia",
            "routing_reason": f"Handoff to Sofia: {task_description}"
        }
    )


@tool
def handoff_to_carlos(
    task_description: Annotated[str, "Description of what Carlos should do next"],
    state: Annotated[MinimalState, InjectedState]
) -> Command[Literal["carlos"]]:
    """
    Handoff to Carlos - Lead Qualification Specialist.
    Use when:
    - Lead score is 5-7 (warm leads)
    - Customer needs qualification
    - Missing budget confirmation or details
    """
    logger.info(f"Handoff to Carlos with task: {task_description}")
    return Command(
        goto="carlos",
        update={
            "agent_task": task_description,
            "next_agent": "carlos",
            "routing_reason": f"Handoff to Carlos: {task_description}"
        }
    )


@tool
def handoff_to_maria(
    task_description: Annotated[str, "Description of what Maria should do next"],
    state: Annotated[MinimalState, InjectedState]
) -> Command[Literal["maria"]]:
    """
    Handoff to Maria - Customer Support Representative.
    Use when:
    - Lead score is 1-4 (cold leads)
    - Customer has general questions
    - Technical issues or complaints
    """
    logger.info(f"Handoff to Maria with task: {task_description}")
    return Command(
        goto="maria",
        update={
            "agent_task": task_description,
            "next_agent": "maria",
            "routing_reason": f"Handoff to Maria: {task_description}"
        }
    )


def create_supervisor_with_proper_state():
    """
    Create a supervisor using create_react_agent with proper state_schema
    """
    model = create_openai_model(temperature=0.0)
    
    tools = [handoff_to_sofia, handoff_to_carlos, handoff_to_maria]
    
    supervisor_prompt = """You are an intelligent routing supervisor for Main Outlet Media.

Current Status:
- Lead Score: {lead_score}/10 ({lead_category})
- Score Reasoning: {score_reasoning}

Extracted Information:
{extracted_info}

Appointment Qualification:
- Name: {has_name}
- Email: {has_email}
- Budget $300+: {has_budget_300}
- Ready for appointment: {ready_for_appointment}

ROUTING RULES:
1. Route to Sofia when: Score 8+ AND all qualifications met
2. Route to Carlos when: Score 5-7 OR missing qualifications
3. Route to Maria when: Score 1-4 OR general questions

Use the handoff tools with clear task descriptions. For example:
- "Help customer book appointment for Tuesday at 2pm"
- "Qualify customer's budget and business needs"
- "Answer customer's questions about our services"

IMPORTANT: You MUST use one of the handoff tools. Do not just analyze - take action!"""
    
    # Create agent WITH state_schema to enable InjectedState in tools
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState,  # This is the key fix!
        prompt=supervisor_prompt,
        name="supervisor"
    )
    
    return agent


async def supervisor_node(state: Dict[str, Any]) -> Command:
    """
    Supervisor node that returns Command objects directly
    No more string parsing needed!
    """
    try:
        # Ensure required fields
        if "messages" not in state:
            state["messages"] = []
        if "thread_id" not in state:
            state["thread_id"] = state.get("contact_id", "unknown")
        if "remaining_steps" not in state:
            state["remaining_steps"] = 10
            
        # Format extracted info for prompt
        extracted_data = state.get("extracted_data", {})
        extracted_info = "\n".join([
            f"Name: {extracted_data.get('name', 'NOT PROVIDED')}",
            f"Business: {extracted_data.get('business_type', 'NOT PROVIDED')}",
            f"Budget: {extracted_data.get('budget', 'NOT PROVIDED')}",
            f"Email: {extracted_data.get('email', 'NOT PROVIDED')}"
        ])
        
        # Check qualifications
        has_email = bool(extracted_data.get("email"))
        has_budget_300 = bool(extracted_data.get("budget") and ("300" in str(extracted_data["budget"])))
        has_name = bool(extracted_data.get("name"))
        
        # Prepare state for agent with all required fields
        agent_state = {
            **state,
            "lead_score": state.get("lead_score", 0),
            "lead_category": state.get("lead_category", "unknown"),
            "score_reasoning": state.get("score_reasoning", "No scoring available"),
            "extracted_info": extracted_info,
            "has_name": "✓" if has_name else "✗",
            "has_email": "✓" if has_email else "✗",
            "has_budget_300": "✓" if has_budget_300 else "✗",
            "ready_for_appointment": "YES" if all([has_name, has_email, has_budget_300]) else "NO"
        }
        
        # Create supervisor
        supervisor = create_supervisor_with_proper_state()
        
        # Run supervisor - it will return a Command object
        result = await supervisor.ainvoke(agent_state)
        
        # The result should contain a Command in the messages
        # The Command is automatically handled by LangGraph
        logger.info("Supervisor completed with Command routing")
        
        # Return the result which contains the Command
        return result
        
    except Exception as e:
        logger.error(f"Error in supervisor: {str(e)}", exc_info=True)
        # Default to Maria on error
        return Command(
            goto="maria",
            update={
                "next_agent": "maria",
                "agent_task": "Handle customer inquiry",
                "routing_reason": f"Error in supervisor: {str(e)}",
                "error": str(e)
            }
        )


# Export the official node name for compatibility
supervisor_official_node = supervisor_node
supervisor_fixed_node = supervisor_node  # Alias for fixed version


__all__ = ["supervisor_node", "supervisor_official_node", "supervisor_fixed_node", "create_supervisor_with_proper_state"]