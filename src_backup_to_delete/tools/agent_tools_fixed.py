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

logger = get_logger("agent_tools_fixed")


# ============ AGENT ESCALATION TOOLS ============
@tool
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
@tool
def get_contact_details_with_task(
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
        contact = ghl_client.get_contact(contact_id)
        
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


@tool
def update_contact_with_context(
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
        result = ghl_client.update_contact(contact_id, updates)
        
        # Add note about the update
        note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Update: {context}"
        ghl_client.add_contact_note(contact_id, note)
        
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
@tool
def book_appointment_with_instructions(
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
        # For now, return a structured response
        # In production, this would integrate with GHL calendar API
        
        return {
            "success": True,
            "contact_id": contact_id,
            "appointment_request": appointment_request,
            "special_instructions": special_instructions,
            "status": "pending_confirmation",
            "message": f"Appointment request received: {appointment_request}"
        }
        
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "contact_id": contact_id
        }


# ============ CONTEXT SAVING TOOLS ============
@tool
def save_important_context(
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
        result = ghl_client.add_contact_note(contact_id, note)
        
        # Also update custom fields if it's high importance
        if importance == "high":
            custom_field_key = f"ai_{context_type}"
            ghl_client.update_contact(contact_id, {
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


# Export all tools
__all__ = [
    "escalate_to_supervisor",
    "get_contact_details_with_task",
    "update_contact_with_context",
    "book_appointment_with_instructions",
    "save_important_context"
]