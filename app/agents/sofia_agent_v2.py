"""
Sofia - Appointment Setting Agent (MODERNIZED VERSION)
Using create_react_agent and latest LangGraph patterns
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import appointment_tools_v2
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("sofia_v2")


from typing import Optional

class SofiaState(AgentState):
    """Extended state for Sofia agent"""
    contact_id: str
    contact_name: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    appointment_datetime: Optional[str]
    should_continue: bool = True


def sofia_prompt(state: SofiaState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Sofia that includes context from state
    """
    # Build context from state
    contact_name = state.get("contact_name", "there")
    appointment_status = state.get("appointment_status")
    
    # Customize prompt based on state
    context = ""
    if appointment_status == "booked":
        context = "\nIMPORTANT: An appointment has already been booked. Focus on confirming details and wrapping up."
    elif contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}."
    
    system_prompt = f"""You are Sofia, a professional appointment setter for Main Outlet Media.

⚠️ CRITICAL APPOINTMENT REQUIREMENTS - NO EXCEPTIONS:
Before booking ANY appointment, you MUST have:
1. ✓ Full Name
2. ✓ Email (for Google Meet link)
3. ✓ Budget $300+/month CONFIRMED

NEVER book appointments without ALL three requirements!

Your workflow:
1. Check what information you already have
2. Gather missing requirements in order (name → email → budget)
3. Only proceed to scheduling when ALL requirements are met

Scripts for missing info:
- Missing name: "Para personalizar tu consulta, ¿cuál es tu nombre completo?"
- Missing email: "{contact_name}, perfecto! Necesito tu email para enviarte el link de Google Meet"
- Missing budget: "{contact_name}, trabajo con presupuestos desde $300/mes, ¿te funciona?"

When qualified (has all 3):
- Check existing appointments first using get_contact_details_v2
- Use calendar tools to check availability
- Present 2-3 time options clearly
- Use book_appointment_and_end to finalize

Important guidelines:
- If user wants to schedule but missing info, ask for it first
- Transfer to Carlos if they need budget qualification
- Transfer to Maria for general support
- Quality over speed - ensure full qualification
{context}

Remember: Only QUALIFIED appointments create success."""
    
    # Return system message plus conversation history
    return [{"role": "system", "content": system_prompt}] + state["messages"]


# Create Sofia agent using create_react_agent
def create_sofia_agent():
    """Factory function to create Sofia agent"""
    settings = get_settings()
    
    # Agent configuration with tracing
    agent_config = {
        "tags": ["agent:sofia", "hot-leads", "appointments"],
        "metadata": {"agent_type": "appointment_setter"}
    }
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
        tools=appointment_tools_v2,
        state_schema=SofiaState,
        prompt=sofia_prompt,
        name="sofia"
    )
    
    logger.info("Created Sofia agent with create_react_agent and tracing enabled")
    return agent


# Node wrapper for StateGraph compatibility
async def sofia_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Sofia agent node for LangGraph - modernized version
    Returns Command for routing or state updates
    """
    try:
        # Create the agent
        agent = create_sofia_agent()
        
        # Invoke the agent
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Sofia processed message for contact {state.get('contact_id')}")
        
        # Check if we should end the conversation
        if result.get("appointment_status") == "booked" and not result.get("should_continue", True):
            logger.info("Appointment booked, ending conversation")
            return Command(
                goto="end",
                update=result
            )
        
        # Otherwise continue normally
        return result
        
    except Exception as e:
        logger.error(f"Error in Sofia agent: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize, but I'm experiencing technical difficulties. "
                          "Please try again in a moment or contact support."
            }]
        }


# Standalone Sofia agent instance for direct use
sofia_agent = create_sofia_agent()


__all__ = ["sofia_node_v2", "sofia_agent", "create_sofia_agent", "SofiaState"]