"""
Simple calendar check tool that returns a string instead of Command
"""
from typing import Optional
from langchain_core.tools import tool
from datetime import datetime, timedelta
import pytz
from app.utils.simple_logger import get_logger
from app.tools.calendar_slots import generate_available_slots, format_slots_for_customer
from app.tools.ghl_client import ghl_client

logger = get_logger("calendar_check_simple")


@tool
async def check_calendar_simple(
    num_slots: int = 3,
    language: str = "es"
) -> str:
    """
    Check calendar availability and return formatted slots.
    Simple version that returns a string for use with create_react_agent.
    
    Args:
        num_slots: Number of slots to return (default 3)
        language: Language for formatting (es/en)
        
    Returns:
        Formatted string with available times
    """
    logger.info(f"📅 CHECK_CALENDAR_SIMPLE called")
    logger.info(f"  - Num slots: {num_slots}")
    logger.info(f"  - Language: {language}")
    
    try:
        # Try to get real slots from GHL first
        start_date = datetime.now(pytz.timezone("America/New_York"))
        end_date = start_date + timedelta(days=7)
        
        ghl_slots = await ghl_client.get_calendar_slots(start_date, end_date)
        
        # If no real slots, generate some
        if not ghl_slots:
            logger.info("Using generated slots as GHL API didn't return any")
            slots = generate_available_slots(num_slots=num_slots)
        else:
            # GHL slots are already in our format from the client
            slots = ghl_slots[:num_slots]
        
        # Format slots for customer
        formatted_message = format_slots_for_customer(slots, language)
        
        logger.info(f"✅ Returning formatted slots")
        return formatted_message
        
    except Exception as e:
        logger.error(f"Error checking calendar: {str(e)}")
        # Fallback to generated slots
        slots = generate_available_slots(num_slots=num_slots)
        formatted_message = format_slots_for_customer(slots, language)
        return formatted_message