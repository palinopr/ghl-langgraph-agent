"""
Carlos Agent v2 - QUALIFICATION SPECIALIST
This agent qualifies leads and ensures $300+ budget before passing to Sofia
Based on n8n workflow requirements
"""
from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import AnyMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic import BaseModel, Field
from typing_extensions import Annotated, Literal, TypedDict
from langgraph.graph.message import add_messages

# Import tools and utilities
from app.tools.agent_tools_v2 import qualification_tools_v2
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("carlos_v2_qualified")


class CarlosState(TypedDict):
    """State for Carlos with qualification tracking"""
    messages: Annotated[list[AnyMessage], add_messages]
    contact_id: str
    contact_name: Optional[str]
    contact_email: Optional[str]
    business_type: Optional[str]
    budget_range: Optional[str]
    budget_confirmed: bool
    qualification_score: int
    qualification_status: Optional[str]


def carlos_prompt(state: CarlosState) -> list[AnyMessage]:
    """
    Dynamic prompt for Carlos focused on $300+ qualification
    """
    contact_name = state.get("contact_name", "amigo")
    business_type = state.get("business_type", "tu negocio")
    budget = state.get("budget_range", "NO CONFIRMADO")
    
    qualification_summary = f"""
CURRENT QUALIFICATION STATUS:
• Name: {state.get("contact_name", "NEEDS COLLECTION")}
• Business: {state.get("business_type", "NEEDS IDENTIFICATION")}
• Budget: {budget} {"✓ QUALIFIED" if state.get("budget_confirmed") else "❌ NEEDS $300+ CONFIRMATION"}
• Email: {state.get("contact_email", "Sofia will collect")}
• Score: {state.get("qualification_score", 0)}/10
"""
    
    system_prompt = f"""You are Carlos, Main Outlet Media's qualification specialist.

YOUR SINGLE MISSION: Qualify leads at $300+/month budget minimum.

{qualification_summary}

QUALIFICATION PRIORITIES:
1. Business Understanding (what they do)
2. Pain Points (what wastes their time)
3. BUDGET QUALIFICATION (critical!)

BUDGET CONVERSATION FLOW:
- Soft intro: "Para ofrecerte la mejor solución..."
- Direct ask: "Trabajo con presupuestos desde $300 al mes, ¿te funciona?"
- If hesitant: "Es una inversión que se paga sola con los clientes que no pierdes"
- If yes: Mark as qualified → Transfer to Sofia
- If no: "Entiendo. Cuando estés listo para invertir en tu crecimiento, aquí estaré"

KEY PHRASES FOR BUDGET:
- "como unos $300" → QUALIFIED
- "sí" (after budget question) → QUALIFIED
- "300 o más" → QUALIFIED
- "no tengo presupuesto" → NOT QUALIFIED
- "es mucho" → OBJECTION HANDLING needed

TRANSFER RULES:
- Budget confirmed $300+ → transfer_to_sofia
- General questions → transfer_to_maria
- Not qualified → Polite closure

Remember: No budget confirmation = No appointment. Quality over quantity."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


# Custom qualification checking tool
@tool
async def check_qualification_status(
    state: Annotated[CarlosState, InjectedState]
) -> str:
    """
    Check if lead is qualified for appointment
    """
    has_name = bool(state.get("contact_name"))
    has_business = bool(state.get("business_type"))
    has_budget = state.get("budget_confirmed", False)
    
    if has_budget:
        return "✅ LEAD QUALIFIED! Ready for Sofia to book appointment."
    
    missing = []
    if not has_business:
        missing.append("tipo de negocio")
    if not has_budget:
        missing.append("confirmación de presupuesto $300+")
        
    return f"❌ Not qualified yet. Need: {', '.join(missing)}"


def create_carlos_agent():
    """Create Carlos agent focused on qualification"""
    settings = get_settings()
    
    # Add qualification tool
    enhanced_tools = qualification_tools_v2 + [check_qualification_status]
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
        tools=enhanced_tools,
        state_schema=CarlosState,
        prompt=carlos_prompt,
        name="carlos_qualified"
    )
    
    logger.info("Created Carlos agent with $300+ QUALIFICATION FOCUS")
    return agent


async def carlos_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Carlos node that tracks budget qualification
    """
    try:
        # Initialize budget tracking
        if "budget_confirmed" not in state:
            state["budget_confirmed"] = False
            
        # Check for budget in messages
        messages = state.get("messages", [])
        for msg in messages[-5:]:  # Check recent messages
            if hasattr(msg, "content") and msg.content:
                content = msg.content.lower()
                # Check for budget confirmation patterns
                if "$300" in content or "300" in content:
                    # Check if user confirmed
                    for response in messages[messages.index(msg)+1:]:
                        if hasattr(response, "content"):
                            resp_content = response.content.lower()
                            if any(word in resp_content for word in ["sí", "si", "yes", "claro", "ok", "perfecto"]):
                                state["budget_confirmed"] = True
                                state["budget_range"] = "300+"
                                state["qualification_score"] = max(6, state.get("qualification_score", 0))
                                break
        
        # Create and invoke agent
        agent = create_carlos_agent()
        result = await agent.ainvoke(state)
        
        # Update qualification score based on collected info
        score = state.get("qualification_score", 0)
        if state.get("contact_name"):
            score = max(score, 2)
        if state.get("business_type"):
            score = max(score, 4)
        if state.get("budget_confirmed"):
            score = max(score, 6)
            
        return {
            "messages": result.get("messages", []),
            "budget_confirmed": state.get("budget_confirmed", False),
            "budget_range": state.get("budget_range"),
            "qualification_score": score,
            "qualification_status": "qualified" if state.get("budget_confirmed") else "qualifying"
        }
        
    except Exception as e:
        logger.error(f"Carlos qualified node error: {e}")
        error_msg = AIMessage(
            content="Disculpa, estaba verificando tu información. ¿Me confirmas tu presupuesto?",
            name="carlos"
        )
        return {"messages": [error_msg]}


# Export
__all__ = ["carlos_node_v2", "create_carlos_agent", "CarlosState"]