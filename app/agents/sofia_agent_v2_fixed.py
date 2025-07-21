"""
Sofia - Appointment Setting Agent (FIXED VERSION)
Simplified to prioritize tool usage for calendar and booking
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import (
    get_contact_details_v2,
    update_contact_with_state,
    book_appointment_from_confirmation,
    create_appointment_v2,
    escalate_to_supervisor
)
from app.tools.appointment_booking_simple import book_appointment_simple
from app.tools.calendar_check_simple import check_calendar_simple
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result

logger = get_logger("sofia_v2_fixed")


class SofiaState(AgentState):
    """Extended state for Sofia agent"""
    contact_id: str
    contact_name: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    appointment_datetime: Optional[str]
    should_continue: bool = True
    extracted_data: Optional[Dict[str, Any]] = {}


def sofia_prompt_simplified(state: SofiaState) -> list[AnyMessage]:
    """
    Simplified prompt that prioritizes tool usage
    """
    messages = state.get("messages", [])
    current_message = ""
    
    # Get most recent human message
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == "human":
            current_message = msg.content
            break
    
    # Get contact info
    contact_id = state.get("contact_id", "unknown")
    contact_name = state.get("contact_name") or state.get("extracted_data", {}).get("name", "Cliente")
    contact_email = state.get("extracted_data", {}).get("email", "")
    
    # Check for appointment-related keywords
    appointment_keywords = [
        "horarios", "disponibles", "horas", "cuándo", "cuando",
        "qué días", "que dias", "appointment", "schedule", "available",
        "agendar", "cita", "llamada", "reunion", "reunión"
    ]
    
    time_selection_keywords = [
        "2pm", "10am", "11am", "4pm", "martes", "miércoles", "jueves",
        "lunes", "viernes", "mañana", "tarde", "perfecto", "está bien",
        "si", "sí", "claro", "ok", "primera", "segunda", "tercera"
    ]
    
    asks_for_appointment = any(kw in current_message.lower() for kw in appointment_keywords)
    selects_time = any(kw in current_message.lower() for kw in time_selection_keywords)
    
    # Check if last AI message offered times
    offered_times = False
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
            content = msg.content.lower() if hasattr(msg, 'content') else ""
            if any(time in content for time in ["10:00", "2:00", "4:00", "disponibles", "horarios"]):
                offered_times = True
                break
    
    # Build action instruction
    if asks_for_appointment:
        action = "USE_CALENDAR_TOOL"
    elif selects_time and offered_times:
        action = "USE_BOOKING_TOOL"
    else:
        action = "NORMAL_RESPONSE"
    
    system_prompt = f"""You are Sofia, an appointment booking specialist for Main Outlet Media.

CURRENT CONTEXT:
- Contact ID: {contact_id}
- Contact Name: {contact_name}
- Contact Email: {contact_email or 'Not provided'}
- Current Message: "{current_message}"
- Action Required: {action}

CRITICAL INSTRUCTIONS:
{
'🚨 CUSTOMER WANTS APPOINTMENT TIMES! Use check_calendar_availability tool IMMEDIATELY!' if action == "USE_CALENDAR_TOOL"
else f'🚨 CUSTOMER SELECTED A TIME! Use book_appointment_simple tool IMMEDIATELY with:\n- customer_confirmation: "{current_message}"\n- contact_id: "{contact_id}"\n- contact_name: "{contact_name}"\n- contact_email: "{contact_email or "noemail@example.com"}"' if action == "USE_BOOKING_TOOL"
else '''
Respond naturally to continue the conversation. You help with:
- WhatsApp automation for businesses
- Appointment scheduling when requested
- Information about our services

Keep responses short and friendly.
'''
}

AVAILABLE TOOLS:
- check_calendar_simple: Shows available appointment times
- book_appointment_simple: Books appointment when customer selects a time
- get_contact_details_v2: Get contact information
- escalate_to_supervisor: Transfer to another agent if needed

IMPORTANT: When ACTION is USE_CALENDAR_TOOL or USE_BOOKING_TOOL, you MUST use the specified tool."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_sofia_agent_fixed():
    """Factory function to create fixed Sofia agent"""
    
    # Use explicit model initialization
    model = create_openai_model(temperature=0.0)
    
    # Simplified tools list
    tools = [
        check_calendar_simple,  # Use simple version that returns string
        book_appointment_simple,
        get_contact_details_v2,
        escalate_to_supervisor
    ]
    
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=SofiaState,
        prompt=sofia_prompt_simplified,
        name="sofia_fixed"
    )
    
    logger.info("Created fixed Sofia agent with simplified prompt")
    return agent


async def sofia_node_v2_fixed(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Fixed Sofia agent node that prioritizes tool usage
    """
    try:
        logger.info(f"Sofia (fixed) processing message for {state.get('contact_id')}")
        
        # Get the current message
        webhook_data = state.get("webhook_data", {})
        current_message = webhook_data.get("message", "").lower()
        
        # Log what we're processing
        logger.info(f"Processing message: '{current_message}'")
        
        # Create and invoke the agent
        agent = create_sofia_agent_fixed()
        result = await agent.ainvoke(state)
        
        logger.info(f"Sofia (fixed) completed processing")
        
        # Check if appointment was booked
        if result.get("appointment_status") == "booked":
            logger.info("Appointment booked successfully!")
            return Command(
                goto="end",
                update=result
            )
        
        # Return filtered result
        return filter_agent_result(result)
        
    except Exception as e:
        logger.error(f"Error in Sofia fixed agent: {str(e)}", exc_info=True)
        
        return {
            "error": str(e),
            "messages": state["messages"] + [AIMessage(
                content="Disculpa, tuve un problema técnico. ¿Podrías repetir tu mensaje?",
                name="sofia"
            )]
        }


# Export functions
__all__ = ["sofia_node_v2_fixed", "create_sofia_agent_fixed", "SofiaState"]