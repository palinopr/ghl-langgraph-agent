"""
Sofia Agent v2 - QUALIFIED APPOINTMENTS ONLY
This agent ONLY books appointments with fully qualified leads
Based on n8n workflow requirements
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import pytz
from langchain_core.messages import AnyMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from typing_extensions import Annotated, Literal, TypedDict
from langgraph.graph import END
from langgraph.types import InjectedState, InjectedStore, InjectedToolCallId
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

# Import tools and utilities
from app.tools.agent_tools_v2 import appointment_tools_v2
from app.tools.ghl_client import GHLClient
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("sofia_v2_qualified")


class SofiaState(TypedDict):
    """Extended state for Sofia agent with qualification tracking"""
    messages: Annotated[list[AnyMessage], add_messages]
    contact_id: str
    contact_name: Optional[str]
    contact_email: Optional[str]
    budget_confirmed: Optional[bool]
    budget_amount: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    appointment_datetime: Optional[str]
    qualification_checklist: Dict[str, bool]  # Track what's been collected
    should_continue: bool = True


def sofia_prompt(state: SofiaState) -> list[AnyMessage]:
    """
    Dynamic prompt for Sofia that enforces qualification requirements
    """
    # Get qualification status
    checklist = state.get("qualification_checklist", {})
    has_name = checklist.get("has_name", False) or bool(state.get("contact_name"))
    has_email = checklist.get("has_email", False) or bool(state.get("contact_email"))
    has_budget = checklist.get("has_budget", False) or state.get("budget_confirmed", False)
    
    # Build missing requirements list
    missing = []
    if not has_name:
        missing.append("nombre completo")
    if not has_email:
        missing.append("email para Google Meet")
    if not has_budget:
        missing.append("confirmación de presupuesto $300+/mes")
    
    qualification_status = f"""
QUALIFICATION STATUS:
✓ Name: {'YES' if has_name else 'NO - ASK FOR IT'}
✓ Email: {'YES' if has_email else 'NO - ASK FOR IT'}  
✓ Budget $300+: {'YES' if has_budget else 'NO - MUST CONFIRM'}
✓ Can Book?: {'YES - PROCEED' if not missing else f'NO - NEED: {", ".join(missing)}'}
"""
    
    system_prompt = f"""You are Sofia, Main Outlet Media's appointment setter for QUALIFIED LEADS ONLY.

⚠️ CRITICAL APPOINTMENT RULES - NO EXCEPTIONS:
1. NEVER book appointments without ALL three requirements
2. NEVER mention dates/times without email confirmed
3. NEVER say "déjame revisar" - ask for missing info instead

{qualification_status}

YOUR PRIORITY CHECKLIST (in order):
1️⃣ NAME: {state.get("contact_name", "MISSING - ASK NOW")}
2️⃣ EMAIL: {state.get("contact_email", "MISSING - CRITICAL")}
3️⃣ BUDGET: {"CONFIRMED" if has_budget else "NOT CONFIRMED - ASK NOW"}

QUALIFICATION SCRIPT:
- Missing name: "Para personalizar tu consulta, ¿cuál es tu nombre completo?"
- Missing email: "[Name], perfecto! Necesito tu email para enviarte el link de Google Meet"
- Missing budget: "[Name], trabajo con presupuestos desde $300/mes, ¿te funciona?"

WHEN ALL QUALIFIED (name + email + budget):
- Use check_availability tool IMMEDIATELY
- Present 2-3 time options
- Confirm with book_appointment_and_end

RESPONSES BY SCENARIO:
- User says "quiero agendar" but missing email: "¡Excelente! Solo necesito tu email para el link"
- User gives time preference without qualification: "Perfecto, primero necesito [missing info]"
- User seems rushed: "Entiendo tu tiempo es valioso. Rápidamente: [ask for missing info]"

Remember: Quality over quantity. Only qualified appointments create success."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


# Enhanced tool with validation
@tool
async def book_appointment_with_validation(
    contact_id: str,
    appointment_details: Dict[str, Any],
    state: Annotated[SofiaState, InjectedState]
) -> str:
    """
    Book appointment ONLY if lead is qualified
    """
    # Check qualification
    checklist = state.get("qualification_checklist", {})
    has_name = checklist.get("has_name", False) or bool(state.get("contact_name"))
    has_email = checklist.get("has_email", False) or bool(state.get("contact_email"))
    has_budget = checklist.get("has_budget", False) or state.get("budget_confirmed", False)
    
    if not all([has_name, has_email, has_budget]):
        missing = []
        if not has_name:
            missing.append("nombre")
        if not has_email:
            missing.append("email")
        if not has_budget:
            missing.append("confirmación de presupuesto $300+")
            
        return f"No puedo agendar aún. Necesito: {', '.join(missing)}"
    
    # If qualified, proceed with booking
    try:
        ghl_client = GHLClient()
        result = await ghl_client.create_appointment(
            contact_id,
            appointment_details["start_time"],
            appointment_details["end_time"],
            appointment_details.get("title", "Consultation"),
            appointment_details.get("timezone", "America/New_York")
        )
        
        if result:
            confirmation = f"""
✅ ¡Cita CONFIRMADA con lead calificado!
📅 Fecha: {appointment_details['date']}
⏰ Hora: {appointment_details['time']}
📧 Link enviado a: {state.get('contact_email')}
💰 Presupuesto: $300+/mes confirmado

¡Nos vemos pronto, {state.get('contact_name', 'amigo')}! 🎯"""
            return confirmation
        else:
            return "Hubo un problema al agendar. Te contactaré manualmente."
            
    except Exception as e:
        logger.error(f"Error booking qualified appointment: {str(e)}")
        return f"Error técnico. Te contactaré directamente."


# Create Sofia agent with enhanced tools
def create_sofia_agent():
    """Factory function to create qualification-focused Sofia agent"""
    settings = get_settings()
    
    # Add validation tool to the standard tools
    enhanced_tools = appointment_tools_v2 + [book_appointment_with_validation]
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
        tools=enhanced_tools,
        state_schema=SofiaState,
        prompt=sofia_prompt,
        name="sofia_qualified"
    )
    
    logger.info("Created Sofia agent with QUALIFICATION REQUIREMENTS")
    return agent


# Node wrapper that tracks qualification
async def sofia_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Sofia node wrapper with qualification tracking
    """
    try:
        # Initialize qualification checklist if not present
        if "qualification_checklist" not in state:
            state["qualification_checklist"] = {
                "has_name": bool(state.get("contact_name")),
                "has_email": bool(state.get("contact_email")),
                "has_budget": state.get("budget_confirmed", False)
            }
        
        # Create and invoke agent
        agent = create_sofia_agent()
        result = await agent.ainvoke(state)
        
        # Update qualification status based on conversation
        messages = result.get("messages", [])
        for msg in messages:
            if hasattr(msg, "content") and msg.content:
                content_lower = msg.content.lower()
                # Check for email patterns
                if "@" in content_lower and "." in content_lower:
                    state["qualification_checklist"]["has_email"] = True
                # Check for budget confirmation
                if any(word in content_lower for word in ["sí", "si", "yes", "claro"]) and "$300" in str(messages):
                    state["qualification_checklist"]["has_budget"] = True
                    state["budget_confirmed"] = True
        
        # Extract command if present
        last_message = messages[-1] if messages else None
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if hasattr(tool_call, "name") and "transfer" in tool_call.name:
                    return result
        
        # Return state updates
        return {
            "messages": messages,
            "qualification_checklist": state["qualification_checklist"],
            "budget_confirmed": state.get("budget_confirmed", False)
        }
        
    except Exception as e:
        logger.error(f"Sofia qualified node error: {e}")
        error_msg = AIMessage(
            content="Disculpa, necesito verificar tu información. ¿Podrías confirmar tu email y presupuesto?",
            name="sofia"
        )
        return {"messages": [error_msg]}


# Export
__all__ = ["sofia_node_v2", "create_sofia_agent", "SofiaState"]