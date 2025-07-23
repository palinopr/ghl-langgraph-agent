"""
Fixed Agent Tools without InjectedState
Avoids validation errors by not requiring full state injection
"""
from typing import Dict, Any, List, Optional, Literal, Annotated
from datetime import datetime, timedelta
import pytz
from langchain_core.tools import tool
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.utils.langsmith_debug import debugger, log_to_langsmith
from functools import wraps

logger = get_logger("agent_tools")


def tracked_tool(func):
    """Decorator that adds LangSmith tracking to any tool"""
    # For now, just use regular @tool decorator
    # The tracking happens via LangSmith's built-in tool tracking
    return tool(func)


# ============ AGENT ESCALATION TOOLS ============
@tracked_tool
def escalate_to_supervisor(
    reason: Literal["needs_appointment", "wrong_agent", "customer_confused", "qualification_complete"],
    task_description: Annotated[str, "Clear description of what needs to be done next"],
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    Escalate back to supervisor with clear task description.
    Use this when you need to transfer to a different agent.
    
    Args:
        reason: Why escalating (needs_appointment, wrong_agent, etc.)
        task_description: Clear task for the next agent
        details: Additional context
    
    Returns:
        Escalation result
    """
    logger.info(f"Escalating to supervisor: {reason} - {task_description}")
    
    return {
        "status": "escalated",
        "reason": reason,
        "task": task_description,
        "details": details,
        "needs_rerouting": True,
        "escalation_reason": reason,
        "escalation_details": task_description
    }


# ============ GHL CONTACT TOOLS ============
@tracked_tool
async def get_contact_details_with_task(
    contact_id: str,
    task: Annotated[str, "What information to look for"] = "general"
) -> Dict[str, Any]:
    """
    Get contact details from GHL with specific task focus.
    
    Args:
        contact_id: The contact ID in GHL
        task: What specific information to focus on
    
    Returns:
        Contact information
    """
    logger.info(f"Getting contact details for task: {task}")
    
    try:
        # Get contact from GHL
        contact = await ghl_client.get_contact(contact_id)
        
        if not contact:
            return {
                "error": "Contact not found",
                "contact_id": contact_id
            }
        
        # Extract relevant information based on task
        result = {
            "contact_id": contact_id,
            "name": f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip(),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "task": task
        }
        
        # Add custom fields if available
        custom_fields = contact.get("customFields", {})
        if custom_fields:
            result["custom_fields"] = custom_fields
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting contact: {str(e)}")
        return {
            "error": str(e),
            "contact_id": contact_id
        }


@tracked_tool
async def update_contact_with_context(
    contact_id: str,
    updates: Dict[str, Any],
    context: Annotated[str, "Why updating this information"]
) -> Dict[str, Any]:
    """
    Update contact in GHL with context about why.
    
    Args:
        contact_id: The contact ID in GHL
        updates: Fields to update
        context: Why updating this information
    
    Returns:
        Update result
    """
    logger.info(f"Updating contact {contact_id} - Context: {context}")
    
    try:
        # Update the contact
        result = await ghl_client.update_contact(contact_id, updates)
        
        # Add note about the update
        note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Update: {context}"
        await ghl_client.add_contact_note(contact_id, note)
        
        return {
            "success": True,
            "contact_id": contact_id,
            "updates": updates,
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error updating contact: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id
        }


# ============ APPOINTMENT TOOLS ============
@tracked_tool
async def book_appointment_with_instructions(
    contact_id: str,
    appointment_request: Annotated[str, "Customer's appointment request (e.g., 'Tuesday at 2pm')"],
    special_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Book appointment based on customer request.
    
    Args:
        contact_id: The contact ID in GHL
        appointment_request: Customer's appointment request
        special_instructions: Any special instructions
    
    Returns:
        Booking result
    """
    logger.info(f"Booking appointment for {contact_id}: {appointment_request}")
    
    try:
        # TODO: Implement actual GHL calendar integration
        # For now, return a mock response but be honest about it
        logger.warning("Appointment booking not yet implemented - returning mock response")
        
        # Add a note about the appointment request
        note = f"[APPOINTMENT REQUEST] {appointment_request}"
        if special_instructions:
            note += f" | Instructions: {special_instructions}"
        
        # Try to save the note at least
        note_result = await ghl_client.add_contact_note(contact_id, note)
        
        return {
            "success": False,  # Be honest - we didn't actually book it
            "contact_id": contact_id,
            "appointment_request": appointment_request,
            "special_instructions": special_instructions,
            "status": "not_implemented",
            "message": "Lo siento, la función de agendar citas está en desarrollo. Un representante te contactará pronto.",
            "note_saved": note_result is not None
        }
        
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id,
            "message": "Hubo un error al procesar tu solicitud. Un representante te contactará."
        }


# ============ CONTEXT SAVING TOOLS ============
@tracked_tool
async def save_important_context(
    contact_id: str,
    context: Annotated[str, "Important information to remember"],
    context_type: Literal["preference", "business_info", "goal", "constraint"],
    importance: Literal["high", "medium", "low"] = "medium"
) -> Dict[str, Any]:
    """
    Save important context about the customer.
    
    Args:
        contact_id: The contact ID in GHL
        context: Information to save
        context_type: Type of context
        importance: How important this information is
    
    Returns:
        Save result
    """
    logger.info(f"Saving {importance} {context_type} for {contact_id}: {context}")
    
    try:
        # Create a note in GHL
        note = f"[{context_type.upper()}] {context} (Importance: {importance})"
        result = await ghl_client.add_contact_note(contact_id, note)
        
        # Also update custom fields if it's high importance
        if importance == "high":
            custom_field_key = f"ai_{context_type}"
            await ghl_client.update_contact(contact_id, {
                "customFields": {
                    custom_field_key: context
                }
            })
        
        return {
            "success": True,
            "contact_id": contact_id,
            "context_saved": context,
            "type": context_type,
            "importance": importance
        }
        
    except Exception as e:
        logger.error(f"Error saving context: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id
        }


@tracked_tool
async def track_lead_progress(
    contact_id: str,
    score_change: Optional[str] = None,
    data_collected: Optional[str] = None,
    next_steps: Optional[str] = None
) -> Dict[str, Any]:
    """
    Track lead progress and score changes in GHL.
    Use this when the lead score changes or important progress is made.
    
    Args:
        contact_id: GHL contact ID
        score_change: Description of score change (e.g., "Score: 3→5 por interés en demo")
        data_collected: New data collected (e.g., "Nombre: Juan, Negocio: Restaurante")
        next_steps: Next steps planned (e.g., "Agendar demo para mañana")
    
    Returns:
        Tracking result
    """
    logger.info(f"Tracking progress for {contact_id}")
    
    try:
        # Build progress note
        note_parts = []
        
        if score_change:
            note_parts.append(f"📊 {score_change}")
        
        if data_collected:
            note_parts.append(f"📋 Datos: {data_collected}")
            
        if next_steps:
            note_parts.append(f"➡️ Siguiente: {next_steps}")
        
        if note_parts:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            note = f"[{timestamp}] " + " | ".join(note_parts)
            
            # Add note to GHL
            result = await ghl_client.add_contact_note(contact_id, note)
            
            return {
                "success": True,
                "contact_id": contact_id,
                "progress_tracked": note
            }
        else:
            return {
                "success": True,
                "contact_id": contact_id,
                "message": "No progress to track"
            }
            
    except Exception as e:
        logger.error(f"Error tracking progress: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id
        }


# Export all tools
__all__ = [
    "escalate_to_supervisor",
    "get_contact_details_with_task",
    "update_contact_with_context",
    "book_appointment_with_instructions",
    "save_important_context",
    "track_lead_progress"
]