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

logger = get_logger("supervisor")


class SupervisorState(MessagesState):
    """State for supervisor with routing information"""
    current_agent: str | None
    next_agent: str | None
    routing_reason: str | None
    conversation_summary: str | None


def supervisor_prompt(state: SupervisorState) -> list[AnyMessage]:
    """
    Dynamic prompt for the supervisor based on current state
    """
    current = state.get("current_agent", "none")
    
    system_prompt = f"""You are an intelligent routing supervisor for Main Outlet Media.
Your role is to analyze conversations and route to the appropriate specialist agent.

Current agent: {current}

Available agents and their specialties:
1. **Sofia** - Appointment Setting Specialist
   - Routes: appointment booking, scheduling, calendar inquiries
   - Keywords: book, schedule, appointment, meeting, consultation, available times
   - Use transfer_to_sofia tool
   
2. **Carlos** - Lead Qualification Specialist  
   - Routes: business information gathering, needs assessment, qualification
   - Keywords: business, company, challenges, goals, budget, marketing needs
   - Use transfer_to_carlos tool
   
3. **Maria** - Customer Support Representative
   - Routes: general inquiries, support issues, complaints, basic information
   - Keywords: help, question, problem, issue, services, information
   - Use transfer_to_maria tool

Decision Guidelines:
- Analyze the user's intent and message content
- Consider the conversation history and context
- If an agent is already handling effectively, let them continue
- Only transfer when there's a clear need for different expertise
- Use the appropriate transfer tool based on your analysis

IMPORTANT: You must use one of the transfer tools to route the conversation.
Do not try to answer questions yourself - always delegate to a specialist."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_supervisor_agent():
    """Create the supervisor agent"""
    settings = get_settings()
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
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
                return Command(goto=END, update=result)
        
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