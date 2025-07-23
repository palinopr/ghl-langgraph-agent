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
def escalate_to_router(
    reason: Literal["needs_appointment", "wrong_agent", "customer_confused", "qualification_complete"],
    task_description: Annotated[str, "Clear description of what needs to be done next"],
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    Escalate back to smart router with clear task description.
    Use this when you need to transfer to a different agent.
    
    Args:
        reason: Why escalating (needs_appointment, wrong_agent, etc.)
        task_description: Clear task for the next agent
        details: Additional context
    
    Returns:
        Escalation result
    """
    logger.info(f"Escalating to router: {reason} - {task_description}")
    
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
        from app.tools.calendar_slots import (
            generate_available_slots,
            parse_spanish_datetime,
            find_matching_slot,
            format_slot_for_spanish
        )
        from app.config import get_settings
        settings = get_settings()
        
        # Parse customer's preferred time
        preferred_time = parse_spanish_datetime(appointment_request)
        
        # Generate available slots
        available_slots = generate_available_slots(
            num_slots=5,
            start_hour=9,
            end_hour=18,
            timezone="America/New_York"
        )
        
        # Find best matching slot
        selected_slot = find_matching_slot(available_slots, appointment_request)
        
        if not selected_slot:
            logger.warning("No available slots found")
            return {
                "success": False,
                "contact_id": contact_id,
                "message": "Lo siento, no tengo horarios disponibles esta semana. Un representante te contactará pronto.",
                "status": "no_availability"
            }
        
        # Format appointment details
        appointment_title = f"Demo - {settings.service_type}"
        if special_instructions:
            appointment_title += f" ({special_instructions})"
        
        # Create appointment in GHL
        appointment_data = {
            "calendarId": settings.ghl_calendar_id,
            "contactId": contact_id,
            "title": appointment_title,
            "startTime": selected_slot["startTime"].isoformat(),
            "endTime": selected_slot["endTime"].isoformat(),
            "appointmentStatus": "confirmed",
            "assignedUserId": settings.ghl_assigned_user_id,
            "notes": f"Requested: {appointment_request}\nBooked via: AI Assistant"
        }
        
        # Call GHL API to create appointment
        result = await ghl_client.create_appointment(appointment_data)
        
        if result and result.get("id"):
            # Success! Add confirmation note
            formatted_time = format_slot_for_spanish(selected_slot)
            confirmation_note = f"✅ DEMO CONFIRMADA: {formatted_time} | ID: {result['id']}"
            await ghl_client.add_contact_note(contact_id, confirmation_note)
            
            # Update contact with appointment info
            await ghl_client.update_contact(contact_id, {
                "customFields": {
                    settings.preferred_day_field_id: selected_slot["startTime"].strftime("%A"),
                    settings.preferred_time_field_id: selected_slot["startTime"].strftime("%I:%M %p")
                }
            })
            
            return {
                "success": True,
                "contact_id": contact_id,
                "appointment_id": result["id"],
                "appointment_time": formatted_time,
                "message": f"¡Perfecto! Tu demo está confirmada para {formatted_time}. Te enviaré un recordatorio.",
                "status": "confirmed"
            }
        else:
            # Fallback: Save as note if API fails
            note = f"[CITA SOLICITADA] {appointment_request} - Confirmar manualmente"
            await ghl_client.add_contact_note(contact_id, note)
            
            return {
                "success": False,
                "contact_id": contact_id,
                "message": "Estoy procesando tu solicitud. Un representante confirmará tu cita pronto.",
                "status": "pending_confirmation"
            }
        
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}", exc_info=True)
        
        # Always try to save the request as a note
        try:
            fallback_note = f"[ERROR AL AGENDAR] {appointment_request} - Contactar manualmente"
            await ghl_client.add_contact_note(contact_id, fallback_note)
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id,
            "message": "Hubo un problema técnico. Un representante te contactará para confirmar tu cita.",
            "status": "error"
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
    "escalate_to_router",
    "get_contact_details_with_task",
    "update_contact_with_context",
    "book_appointment_with_instructions",
    "save_important_context",
    "track_lead_progress"
]