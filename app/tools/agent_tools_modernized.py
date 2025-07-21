"""
Modernized Agent Tools with Enhanced Command Pattern
Implements task descriptions and proper Command usage for all tools
"""
from typing import Dict, Any, List, Optional, Literal, Annotated
from datetime import datetime, timedelta
import pytz
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, AIMessage
from langgraph.prebuilt import InjectedState, InjectedToolCallId
from langgraph.types import Command
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.state.conversation_state import ConversationState

logger = get_logger("agent_tools_modernized")


# ============ AGENT ESCALATION TOOLS ============
@tool
def escalate_to_supervisor(
    reason: Literal["needs_appointment", "wrong_agent", "customer_confused", "qualification_complete"],
    task_description: Annotated[str, "Clear description of what needs to be done next"],
    details: Optional[str] = None,
    state: Annotated[ConversationState, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """
    Escalate back to supervisor with clear task description.
    Use this when you need to transfer to a different agent.
    
    Args:
        reason: Why escalating (needs_appointment, wrong_agent, etc.)
        task_description: Clear task for the next agent (e.g., "Book appointment for Tuesday 2pm")
        details: Additional context
        state: Current conversation state
        tool_call_id: Tool call ID for tracking
    
    Returns:
        Command to route back to supervisor
    """
    logger.info(f"Escalating to supervisor: {reason} - {task_description}")
    
    # Create tool message
    tool_message = ToolMessage(
        content=f"Escalating: {reason} - {task_description}",
        tool_call_id=tool_call_id
    )
    
    # Return command with task description
    return Command(
        goto="supervisor",
        update={
            "messages": [tool_message],
            "needs_rerouting": True,
            "escalation_reason": reason,
            "escalation_details": details or task_description,
            "agent_task": task_description,
            "escalation_from": state.get("current_agent", "unknown")
        },
        graph=Command.PARENT
    )


# ============ CONTACT MANAGEMENT TOOLS ============
@tool
async def get_contact_details_with_task(
    contact_id: str,
    task: Annotated[str, "What information to look for"] = "general",
    state: Annotated[ConversationState, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """
    Get contact details from GHL with specific task focus.
    
    Args:
        contact_id: GHL contact ID
        task: What to look for (e.g., "check previous appointments", "verify budget")
        state: Current state
        tool_call_id: Tool call ID
    
    Returns:
        Command with contact details update
    """
    try:
        logger.info(f"Getting contact details for task: {task}")
        
        # Get contact from GHL
        contact = await ghl_client.get_contact(contact_id)
        
        if not contact:
            tool_message = ToolMessage(
                content=f"Contact {contact_id} not found",
                tool_call_id=tool_call_id
            )
            return Command(
                update={"messages": [tool_message]},
                graph=Command.PARENT
            )
        
        # Extract relevant info based on task
        relevant_info = {
            "name": contact.get("name") or contact.get("firstName"),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "tags": contact.get("tags", [])
        }
        
        # Add custom fields if checking budget/business
        if "budget" in task.lower() or "business" in task.lower():
            custom_fields = contact.get("customFields", {})
            relevant_info.update({
                "business_type": custom_fields.get("business_type"),
                "budget": custom_fields.get("budget"),
                "goal": custom_fields.get("goal")
            })
        
        # Create informative message
        info_parts = []
        for key, value in relevant_info.items():
            if value:
                info_parts.append(f"{key}: {value}")
        
        tool_message = ToolMessage(
            content=f"Contact info for {task}: " + ", ".join(info_parts),
            tool_call_id=tool_call_id
        )
        
        return Command(
            update={
                "messages": [tool_message],
                "contact_info": contact,
                "contact_name": relevant_info.get("name"),
                "contact_email": relevant_info.get("email")
            },
            graph=Command.PARENT
        )
        
    except Exception as e:
        logger.error(f"Error getting contact: {str(e)}")
        tool_message = ToolMessage(
            content=f"Error getting contact: {str(e)}",
            tool_call_id=tool_call_id
        )
        return Command(
            update={"messages": [tool_message]},
            graph=Command.PARENT
        )


@tool
async def update_contact_with_context(
    contact_id: str,
    updates: Dict[str, Any],
    context: Annotated[str, "Why updating this information"],
    state: Annotated[ConversationState, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """
    Update contact in GHL with context about why.
    
    Args:
        contact_id: GHL contact ID
        updates: Fields to update
        context: Why updating (e.g., "Customer provided business type during qualification")
        state: Current state
        tool_call_id: Tool call ID
    
    Returns:
        Command with update confirmation
    """
    try:
        logger.info(f"Updating contact for: {context}")
        
        # Update in GHL
        success = await ghl_client.update_contact(contact_id, updates)
        
        if success:
            tool_message = ToolMessage(
                content=f"✓ Updated contact: {context}",
                tool_call_id=tool_call_id
            )
            
            # Also update state with the new values
            state_updates = {"messages": [tool_message]}
            
            # Map common fields to state
            if "name" in updates:
                state_updates["contact_name"] = updates["name"]
            if "email" in updates:
                state_updates["contact_email"] = updates["email"]
            if "customFields" in updates:
                state_updates["extracted_data"] = {
                    **state.get("extracted_data", {}),
                    **updates["customFields"]
                }
        else:
            tool_message = ToolMessage(
                content=f"Failed to update contact: {context}",
                tool_call_id=tool_call_id
            )
            state_updates = {"messages": [tool_message]}
        
        return Command(
            update=state_updates,
            graph=Command.PARENT
        )
        
    except Exception as e:
        logger.error(f"Error updating contact: {str(e)}")
        tool_message = ToolMessage(
            content=f"Error updating contact: {str(e)}",
            tool_call_id=tool_call_id
        )
        return Command(
            update={"messages": [tool_message]},
            graph=Command.PARENT
        )


# ============ APPOINTMENT TOOLS WITH TASK CONTEXT ============
@tool
async def book_appointment_with_instructions(
    contact_id: str,
    appointment_request: Annotated[str, "Customer's appointment request (e.g., 'Tuesday at 2pm')"],
    special_instructions: Optional[str] = None,
    state: Annotated[ConversationState, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """
    Book appointment based on customer's request with special instructions.
    
    Args:
        contact_id: GHL contact ID
        appointment_request: What the customer requested
        special_instructions: Any special notes for the appointment
        state: Current state
        tool_call_id: Tool call ID
    
    Returns:
        Command with appointment confirmation
    """
    try:
        logger.info(f"Booking appointment for request: {appointment_request}")
        
        # Parse the request
        from app.tools.calendar_slots import parse_spanish_datetime
        parsed_time = parse_spanish_datetime(appointment_request)
        
        if not parsed_time:
            # If can't parse, ask for clarification
            tool_message = ToolMessage(
                content="No pude entender la fecha/hora. ¿Podrías especificar el día y hora exactos?",
                tool_call_id=tool_call_id
            )
            return Command(
                update={"messages": [tool_message]},
                graph=Command.PARENT
            )
        
        # Get available slots
        slots = await ghl_client.get_available_slots(
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            timezone="America/New_York"
        )
        
        # Find matching slot
        from app.tools.calendar_slots import find_matching_slot
        matching_slot = find_matching_slot(slots, parsed_time)
        
        if not matching_slot:
            tool_message = ToolMessage(
                content=f"No hay disponibilidad para {appointment_request}. ¿Te gustaría ver otros horarios?",
                tool_call_id=tool_call_id
            )
            return Command(
                update={
                    "messages": [tool_message],
                    "available_slots": slots
                },
                graph=Command.PARENT
            )
        
        # Book the appointment
        appointment_data = {
            "calendarId": ghl_client.calendar_id,
            "contactId": contact_id,
            "startTime": matching_slot["startTime"].isoformat(),
            "endTime": matching_slot["endTime"].isoformat(),
            "title": "Consulta WhatsApp Automation - Main Outlet Media",
            "appointmentStatus": "booked",
            "assignedUserId": ghl_client.assigned_user_id,
            "notes": special_instructions or f"Solicitado: {appointment_request}"
        }
        
        result = await ghl_client.create_appointment(appointment_data)
        
        if result and result.get("id"):
            # Format confirmation
            day = matching_slot["startTime"].strftime("%A %d de %B")
            time = matching_slot["startTime"].strftime("%I:%M %p")
            
            confirmation_msg = f"""¡Perfecto! Tu cita está confirmada:
            
📅 {day}
🕐 {time}
📍 Consulta virtual (recibirás el link por email)
            
Te enviaré un recordatorio 24 horas antes. ¡Gracias por elegir Main Outlet Media!"""
            
            tool_message = ToolMessage(
                content=confirmation_msg,
                tool_call_id=tool_call_id
            )
            
            return Command(
                update={
                    "messages": [tool_message],
                    "appointment_booked": True,
                    "appointment_id": result["id"],
                    "appointment_datetime": matching_slot["startTime"],
                    "should_end": True  # End conversation after booking
                },
                graph=Command.PARENT
            )
        else:
            tool_message = ToolMessage(
                content="Hubo un problema al agendar la cita. ¿Podemos intentar con otro horario?",
                tool_call_id=tool_call_id
            )
            return Command(
                update={"messages": [tool_message]},
                graph=Command.PARENT
            )
            
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        tool_message = ToolMessage(
            content="Disculpa, tuve un problema técnico. ¿Podemos intentar de nuevo?",
            tool_call_id=tool_call_id
        )
        return Command(
            update={"messages": [tool_message]},
            graph=Command.PARENT
        )


# ============ MEMORY/CONTEXT TOOLS ============
@tool
def save_important_context(
    content: str,
    context_type: Literal["preference", "business_info", "goal", "constraint"],
    importance: Literal["high", "medium", "low"] = "medium",
    state: Annotated[ConversationState, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """
    Save important context for future reference.
    
    Args:
        content: What to save
        context_type: Type of information
        importance: How important this is
        state: Current state
        tool_call_id: Tool call ID
    
    Returns:
        Command with context saved
    """
    logger.info(f"Saving {importance} {context_type}: {content}")
    
    # Add to extracted data
    extracted_data = state.get("extracted_data", {})
    
    # Map context types to fields
    field_mapping = {
        "business_info": "business_type",
        "goal": "goal",
        "constraint": "constraints",
        "preference": "preferences"
    }
    
    field = field_mapping.get(context_type, context_type)
    
    # Update or append
    if field in ["constraints", "preferences"]:
        # These are lists
        if field not in extracted_data:
            extracted_data[field] = []
        extracted_data[field].append(content)
    else:
        # Single value
        extracted_data[field] = content
    
    tool_message = ToolMessage(
        content=f"✓ Saved {context_type}: {content}",
        tool_call_id=tool_call_id
    )
    
    return Command(
        update={
            "messages": [tool_message],
            "extracted_data": extracted_data
        },
        graph=Command.PARENT
    )


# ============ COLLECTIONS FOR DIFFERENT AGENTS ============
# Tools for Maria (Support Agent)
maria_tools = [
    escalate_to_supervisor,
    get_contact_details_with_task,
    update_contact_with_context,
    save_important_context
]

# Tools for Carlos (Qualification Agent)
carlos_tools = [
    escalate_to_supervisor,
    get_contact_details_with_task,
    update_contact_with_context,
    save_important_context
]

# Tools for Sofia (Appointment Agent)
sofia_tools = [
    escalate_to_supervisor,
    book_appointment_with_instructions,
    get_contact_details_with_task,
    update_contact_with_context
]

# Export all
__all__ = [
    "escalate_to_supervisor",
    "get_contact_details_with_task",
    "update_contact_with_context",
    "book_appointment_with_instructions",
    "save_important_context",
    "maria_tools",
    "carlos_tools",
    "sofia_tools"
]