"""
Carlos - Lead Qualification Agent (MODERNIZED VERSION)
Using create_react_agent and latest LangGraph patterns
"""
from typing import Dict, Any, List, Annotated
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import qualification_tools_v2
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("carlos_v2")


class CarlosState(AgentState):
    """Extended state for Carlos agent"""
    contact_id: str
    contact_name: str | None
    business_type: str | None
    business_goals: str | None
    budget_range: str | None
    qualification_score: int = 0
    qualification_status: str | None


def carlos_prompt(state: CarlosState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Carlos that includes context from state
    """
    # Build context from state
    contact_name = state.get("contact_name", "there")
    business_type = state.get("business_type")
    
    # Customize based on what we know
    context = ""
    if business_type:
        context = f"\nBusiness Type: {business_type}"
    if contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}.{context}"
    
    system_prompt = f"""You are Carlos, a lead qualification specialist for Main Outlet Media.

Your goal is to understand businesses and qualify leads through friendly conversation.
You should:

1. Build rapport with warm, professional conversation
2. Discover their business type and current challenges
3. Understand their marketing goals and growth plans
4. Assess budget range (tactfully)
5. Identify specific pain points we can solve
6. Qualify leads based on fit (score 1-10)

Qualification criteria:
- Business type alignment (do we serve their industry?)
- Budget availability (can they afford our services?)
- Urgency/timeline (are they ready to move forward?)
- Decision-making authority (are we talking to the right person?)

Important guidelines:
- Be conversational and consultative, not salesy
- Ask open-ended questions to understand their needs
- Use save_conversation_context to store important business info
- Transfer to Sofia if they're ready to book an appointment (score 8-10)
- Transfer to Maria for general support questions
- Share insights about how Main Outlet Media can help
{context}

Focus on building trust and understanding their business deeply."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_carlos_agent():
    """Factory function to create Carlos agent"""
    settings = get_settings()
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
        tools=qualification_tools_v2,
        state_schema=CarlosState,
        prompt=carlos_prompt,
        name="carlos"
    )
    
    logger.info("Created Carlos agent with create_react_agent")
    return agent


async def carlos_node_v2(state: Dict[str, Any]) -> Command | Dict[str, Any]:
    """
    Carlos agent node for LangGraph - modernized version
    Returns Command for routing or state updates
    """
    try:
        # Create the agent
        agent = create_carlos_agent()
        
        # Invoke the agent
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Carlos processed message for contact {state.get('contact_id')}")
        
        # Calculate qualification score based on collected info
        qualification_score = 0
        if result.get("business_type"):
            qualification_score += 2
        if result.get("business_goals"):
            qualification_score += 2
        if result.get("budget_range"):
            qualification_score += 3
        if "ready" in str(result.get("messages", [])).lower():
            qualification_score += 3
            
        # Update qualification status
        if qualification_score >= 8:
            result["qualification_status"] = "hot"
            result["qualification_score"] = qualification_score
            
            # Route to Sofia for appointment booking
            logger.info(f"Lead qualified as hot (score: {qualification_score}), routing to Sofia")
            return Command(
                goto="sofia",
                update={
                    **result,
                    "next_agent": "sofia",
                    "routing_reason": "Hot lead ready for appointment"
                }
            )
        elif qualification_score >= 5:
            result["qualification_status"] = "warm"
            result["qualification_score"] = qualification_score
        else:
            result["qualification_status"] = "cold"
            result["qualification_score"] = qualification_score
        
        # Continue with Carlos by default
        return result
        
    except Exception as e:
        logger.error(f"Error in Carlos agent: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize for the technical issue. Let me connect you with someone who can help."
            }],
            "next_agent": "maria"
        }


# Standalone Carlos agent instance
carlos_agent = create_carlos_agent()


__all__ = ["carlos_node_v2", "carlos_agent", "create_carlos_agent", "CarlosState"]