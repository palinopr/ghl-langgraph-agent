"""
Simple appointment booking tool that works with minimal state
"""
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from datetime import datetime, timedelta
import pytz
from app.utils.simple_logger import get_logger
from app.tools.calendar_slots import parse_spanish_datetime, generate_available_slots, find_matching_slot, format_slot_for_spanish
from app.tools.ghl_client import ghl_client

logger = get_logger("appointment_booking_simple")


@tool
async def book_appointment_simple(
    customer_confirmation: str,
    contact_id: str,
    contact_name: str,
    contact_email: str
) -> str:
    """
    Book appointment based on customer's time selection.
    This is a simplified version that doesn't require full state injection.
    
    Args:
        customer_confirmation: Customer's time selection (e.g., "10:00 AM", "la primera")
        contact_id: GHL contact ID
        contact_name: Contact's name
        contact_email: Contact's email
        
    Returns:
        Confirmation message or error
    """
    logger.info(f"📅 BOOK_APPOINTMENT_SIMPLE called")
    logger.info(f"  - Customer said: '{customer_confirmation}'")
    logger.info(f"  - Contact: {contact_name} ({contact_id})")
    
    try:
        # Generate available slots
        available_slots = generate_available_slots(num_slots=3)
        
        # Find matching slot based on customer preference
        selected_slot = find_matching_slot(available_slots, customer_confirmation)
        if not selected_slot:
            return "No pude entender qué horario prefieres. ¿Puedes especificar si es 10:00 AM, 2:00 PM o 4:00 PM?"
        
        logger.info(f"✅ Selected time slot: {selected_slot['startTime']}")
        
        # Create appointment in GHL
        result = await ghl_client.create_appointment(
            contact_id=contact_id,
            start_time=selected_slot["startTime"],
            end_time=selected_slot["endTime"],
            title=f"Demo WhatsApp Automation - {contact_name}",
            timezone="America/New_York"
        )
        
        if result and "id" in result:
            # Format confirmation message
            formatted_time = format_slot_for_spanish(selected_slot)
            
            google_meet_link = result.get("meetLink", "")
            if google_meet_link:
                confirmation = (
                    f"¡CONFIRMADO! 🎉\n\n"
                    f"📅 {formatted_time}\n"
                    f"📧 Enviaré el enlace a: {contact_email}\n"
                    f"💻 Google Meet: {google_meet_link}\n\n"
                    f"¡Nos vemos pronto!"
                )
            else:
                confirmation = (
                    f"¡CONFIRMADO! 🎉\n\n"
                    f"📅 {formatted_time}\n"
                    f"📧 Enviaré los detalles a: {contact_email}\n\n"
                    f"¡Nos vemos pronto!"
                )
            
            logger.info(f"✅ Appointment created: {result['id']}")
            return confirmation
        else:
            logger.error(f"Failed to create appointment: {result}")
            return "Hubo un problema al agendar la cita. ¿Podemos intentar con otro horario?"
            
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return "Lo siento, hubo un error al agendar. ¿Podemos intentar de nuevo?"