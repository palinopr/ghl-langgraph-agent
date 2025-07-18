"""
LangGraph tool definitions for GoHighLevel agents
These tools will be used by the agents to interact with GoHighLevel
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta
import pytz
from langchain_core.tools import tool
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger

logger = get_logger("agent_tools")


@tool
async def get_contact_details(contact_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a contact from GoHighLevel.
    
    Args:
        contact_id: The unique identifier of the contact
        
    Returns:
        Contact details including name, email, phone, custom fields, and tags
    """
    try:
        contact = await ghl_client.get_contact_details(contact_id)
        if contact:
            logger.info(f"Retrieved contact details for {contact_id}")
            return contact
        else:
            logger.warning(f"No contact found for ID: {contact_id}")
            return {"error": f"Contact {contact_id} not found"}
    except Exception as e:
        logger.error(f"Error getting contact details: {str(e)}")
        return {"error": str(e)}


@tool
async def update_contact_info(
    contact_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update contact information in GoHighLevel.
    
    Args:
        contact_id: The unique identifier of the contact
        updates: Dictionary of fields to update (e.g., {"email": "new@email.com"})
        
    Returns:
        Updated contact information or error
    """
    try:
        result = await ghl_client.update_contact(contact_id, updates)
        if result:
            logger.info(f"Updated contact {contact_id} with: {updates}")
            return result
        else:
            return {"error": "Failed to update contact"}
    except Exception as e:
        logger.error(f"Error updating contact: {str(e)}")
        return {"error": str(e)}


@tool
async def update_custom_fields(
    contact_id: str,
    custom_fields: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update custom fields for a contact in GoHighLevel.
    
    Args:
        contact_id: The unique identifier of the contact
        custom_fields: Dictionary of custom field IDs and their values
        
    Returns:
        Updated contact information or error
    """
    try:
        result = await ghl_client.update_custom_fields(contact_id, custom_fields)
        if result:
            logger.info(f"Updated custom fields for {contact_id}")
            return result
        else:
            return {"error": "Failed to update custom fields"}
    except Exception as e:
        logger.error(f"Error updating custom fields: {str(e)}")
        return {"error": str(e)}


@tool
async def add_contact_tags(
    contact_id: str,
    tags: List[str]
) -> Dict[str, Any]:
    """
    Add tags to a contact in GoHighLevel.
    
    Args:
        contact_id: The unique identifier of the contact
        tags: List of tags to add
        
    Returns:
        Updated contact information or error
    """
    try:
        result = await ghl_client.add_tags(contact_id, tags)
        if result:
            logger.info(f"Added tags {tags} to contact {contact_id}")
            return result
        else:
            return {"error": "Failed to add tags"}
    except Exception as e:
        logger.error(f"Error adding tags: {str(e)}")
        return {"error": str(e)}


@tool
async def send_message(
    contact_id: str,
    message: str,
    message_type: Literal["WhatsApp", "SMS"] = "WhatsApp"
) -> Dict[str, Any]:
    """
    Send a message to a contact via GoHighLevel.
    
    Args:
        contact_id: The unique identifier of the contact
        message: The message content to send
        message_type: Type of message - either "WhatsApp" or "SMS"
        
    Returns:
        Message send result or error
    """
    try:
        result = await ghl_client.send_message(contact_id, message, message_type)
        if result:
            logger.info(f"Sent {message_type} message to {contact_id}")
            return {"success": True, "result": result}
        else:
            return {"error": "Failed to send message"}
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return {"error": str(e)}


@tool
async def get_conversation_history(contact_id: str) -> List[Dict[str, Any]]:
    """
    Get the conversation history for a contact.
    
    Args:
        contact_id: The unique identifier of the contact
        
    Returns:
        List of messages in the conversation
    """
    try:
        messages = await ghl_client.get_conversation_history(contact_id)
        logger.info(f"Retrieved {len(messages)} messages for contact {contact_id}")
        return messages
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return []


@tool
async def check_calendar_availability(
    days_ahead: int = 7,
    timezone: str = "America/New_York"
) -> List[Dict[str, Any]]:
    """
    Check calendar availability for the next specified days.
    
    Args:
        days_ahead: Number of days to check availability (default: 7)
        timezone: Timezone for the calendar check (default: America/New_York)
        
    Returns:
        List of available time slots
    """
    try:
        tz = pytz.timezone(timezone)
        start_date = datetime.now(tz)
        end_date = start_date + timedelta(days=days_ahead)
        
        slots = await ghl_client.check_calendar_availability(
            start_date, end_date, timezone
        )
        
        logger.info(f"Found {len(slots)} available slots")
        return slots
    except Exception as e:
        logger.error(f"Error checking calendar availability: {str(e)}")
        return []


@tool
async def check_existing_appointments(contact_id: str) -> List[Dict[str, Any]]:
    """
    Check if a contact has any existing appointments.
    
    Args:
        contact_id: The unique identifier of the contact
        
    Returns:
        List of existing appointments
    """
    try:
        appointments = await ghl_client.check_existing_appointments(contact_id)
        logger.info(f"Found {len(appointments)} appointments for contact {contact_id}")
        return appointments
    except Exception as e:
        logger.error(f"Error checking appointments: {str(e)}")
        return []


@tool
async def create_appointment(
    contact_id: str,
    start_time: str,
    end_time: str,
    title: str = "Consultation",
    timezone: str = "America/New_York"
) -> Dict[str, Any]:
    """
    Create an appointment for a contact.
    
    Args:
        contact_id: The unique identifier of the contact
        start_time: Appointment start time in ISO format
        end_time: Appointment end time in ISO format
        title: Title of the appointment (default: "Consultation")
        timezone: Timezone for the appointment (default: America/New_York)
        
    Returns:
        Created appointment details or error
    """
    try:
        # Parse times
        tz = pytz.timezone(timezone)
        start_dt = datetime.fromisoformat(start_time).replace(tzinfo=tz)
        end_dt = datetime.fromisoformat(end_time).replace(tzinfo=tz)
        
        result = await ghl_client.create_appointment(
            contact_id, start_dt, end_dt, title, timezone
        )
        
        if result:
            logger.info(f"Created appointment for {contact_id} at {start_time}")
            return result
        else:
            return {"error": "Failed to create appointment"}
    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}")
        return {"error": str(e)}


@tool
async def create_note(
    contact_id: str,
    note_content: str
) -> Dict[str, Any]:
    """
    Create a note for a contact in GoHighLevel.
    
    Args:
        contact_id: The unique identifier of the contact
        note_content: The content of the note
        
    Returns:
        Created note details or error
    """
    try:
        result = await ghl_client.create_note(contact_id, note_content)
        if result:
            logger.info(f"Created note for contact {contact_id}")
            return result
        else:
            return {"error": "Failed to create note"}
    except Exception as e:
        logger.error(f"Error creating note: {str(e)}")
        return {"error": str(e)}


# Tool collection for different agent types
appointment_tools = [
    get_contact_details,
    check_calendar_availability,
    check_existing_appointments,
    create_appointment,
    send_message,
    update_custom_fields,
    add_contact_tags,
    create_note
]

lead_qualification_tools = [
    get_contact_details,
    update_contact_info,
    update_custom_fields,
    add_contact_tags,
    send_message,
    get_conversation_history,
    create_note
]

support_tools = [
    get_contact_details,
    send_message,
    get_conversation_history,
    create_note,
    add_contact_tags
]