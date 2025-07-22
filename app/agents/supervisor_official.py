"""
Official LangGraph Supervisor Pattern
Using langgraph-supervisor library for modern multi-agent orchestration
"""
from typing import Dict, Any, List, Optional, Literal
from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.state.minimal_state import MinimalState
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState

logger = get_logger("supervisor_official")


# Create handoff tools with task descriptions
@tool
def handoff_to_sofia(
    task_description: Annotated[str, "Description of what Sofia should do next"],
    state: Annotated[MinimalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Handoff to Sofia - Appointment Setting Specialist.
    Use when:
    - Lead score is 8-10 (hot leads)
    - Customer is ready to book appointment
    - Has name, email, and $300+ budget confirmed
    """
    logger.info(f"Handoff to Sofia with task: {task_description}")
    # Create tool message for tracking
    tool_message = ToolMessage(
        content=f"Handing off to Sofia: {task_description}",
        tool_call_id=tool_call_id
    )
    return Command(
        goto="sofia",
        update={
            "messages": [tool_message],
            "next_agent": "sofia",
            "agent_task": task_description,
            "routing_reason": f"Handoff to Sofia: {task_description}"
        },
        graph=Command.PARENT,
    )


@tool
def handoff_to_carlos(
    task_description: Annotated[str, "Description of what Carlos should do next"],
    state: Annotated[MinimalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Handoff to Carlos - Lead Qualification Specialist.
    Use when:
    - Lead score is 5-7 (warm leads)
    - Customer needs qualification
    - Missing budget confirmation or details
    """
    logger.info(f"Handoff to Carlos with task: {task_description}")
    # Create tool message for tracking
    tool_message = ToolMessage(
        content=f"Handing off to Carlos: {task_description}",
        tool_call_id=tool_call_id
    )
    return Command(
        goto="carlos",
        update={
            "messages": [tool_message],
            "next_agent": "carlos",
            "agent_task": task_description,
            "routing_reason": f"Handoff to Carlos: {task_description}"
        },
        graph=Command.PARENT,
    )


@tool
def handoff_to_maria(
    task_description: Annotated[str, "Description of what Maria should do next"],
    state: Annotated[MinimalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Handoff to Maria - Customer Support Representative.
    Use when:
    - Lead score is 1-4 (cold leads)
    - Customer has general questions
    - Technical issues or complaints
    """
    logger.info(f"Handoff to Maria with task: {task_description}")
    # Create tool message for tracking
    tool_message = ToolMessage(
        content=f"Handing off to Maria: {task_description}",
        tool_call_id=tool_call_id
    )
    return Command(
        goto="maria",
        update={
            "messages": [tool_message],
            "next_agent": "maria",
            "agent_task": task_description,
            "routing_reason": f"Handoff to Maria: {task_description}"
        },
        graph=Command.PARENT,
    )


def create_official_supervisor():
    """
    Create supervisor using official pattern with handoff tools
    """
    # This function now just returns the tool-based supervisor
    return create_supervisor_with_tools()


def create_supervisor_with_tools():
    """
    Create a supervisor using create_react_agent with handoff tools
    """
    model = create_openai_model(temperature=0.0)
    
    tools = [handoff_to_sofia, handoff_to_carlos, handoff_to_maria]
    
    def supervisor_prompt(state: MinimalState) -> List[AnyMessage]:
        """Dynamic prompt based on state"""
        lead_score = state.get("lead_score", 0)
        lead_category = state.get("lead_category", "unknown")
        score_reasoning = state.get("score_reasoning", "No scoring available")
        extracted_data = state.get("extracted_data", {})
        
        # Build context
        context_parts = []
        if extracted_data.get("name"):
            context_parts.append(f"Name: {extracted_data['name']}")
        if extracted_data.get("business_type"):
            context_parts.append(f"Business: {extracted_data['business_type']}")
        if extracted_data.get("budget"):
            context_parts.append(f"Budget: {extracted_data['budget']}")
        if extracted_data.get("email"):
            context_parts.append(f"Email: {extracted_data['email']}")
            
        context_str = "\n".join(context_parts) if context_parts else "No information extracted yet"
        
        # Check qualifications
        has_email = bool(extracted_data.get("email"))
        has_budget_300 = bool(extracted_data.get("budget") and ("300" in str(extracted_data["budget"])))
        has_name = bool(extracted_data.get("name"))
        
        system_prompt = f"""You are an intelligent routing supervisor for Main Outlet Media.

Current Status:
- Lead Score: {lead_score}/10 ({lead_category})
- Score Reasoning: {score_reasoning}

Extracted Information:
{context_str}

Appointment Qualification:
- Name: {"✓" if has_name else "✗"}
- Email: {"✓" if has_email else "✗"}
- Budget $300+: {"✓" if has_budget_300 else "✗"}
- Ready for appointment: {"YES" if all([has_name, has_email, has_budget_300]) else "NO"}

ROUTING RULES:
1. Route to Sofia when: Score 8+ AND all qualifications met
2. Route to Carlos when: Score 5-7 OR missing qualifications
3. Route to Maria when: Score 1-4 OR general questions

Use the handoff tools with clear task descriptions. For example:
- "Help customer book appointment for Tuesday at 2pm"
- "Qualify customer's budget and business needs"
- "Answer customer's questions about our services"

IMPORTANT: You MUST use one of the handoff tools. Do not just analyze - take action!"""
        
        return [{"role": "system", "content": system_prompt}] + state["messages"]
    
    # Create agent
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState,
        prompt=supervisor_prompt,
        name="supervisor_official"
    )
    
    return agent


async def supervisor_official_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor node using official patterns
    Returns state updates for routing
    """
    try:
        # Create supervisor with tools
        supervisor = create_supervisor_with_tools()
        
        # Run supervisor - it will use handoff tools that return Commands
        result = await supervisor.ainvoke(state)
        
        # The result contains all state updates from the agent
        updates = {}
        
        # Copy all relevant fields from result
        if "messages" in result:
            updates["messages"] = result["messages"]
        if "next_agent" in result:
            updates["next_agent"] = result["next_agent"]
        if "agent_task" in result:
            updates["agent_task"] = result["agent_task"]
        if "routing_reason" in result:
            updates["routing_reason"] = result["routing_reason"]
            
        # Mark supervisor as complete
        updates["supervisor_complete"] = True
        
        logger.info(f"Supervisor routing to: {updates.get('next_agent', 'none')} with task: {updates.get('agent_task', 'none')}")
        return updates
        
    except Exception as e:
        logger.error(f"Error in official supervisor: {str(e)}", exc_info=True)
        # Default to Maria on error
        return {
            "next_agent": "maria",
            "supervisor_complete": True,
            "error": str(e)
        }


__all__ = ["supervisor_official_node", "create_official_supervisor", "create_supervisor_with_tools"]