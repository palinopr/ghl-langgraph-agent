"""
Calendar slot checking functionality for GHL appointments
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
from app.utils.simple_logger import get_logger

logger = get_logger("calendar_slots")


def parse_spanish_datetime(text: str, timezone: str = "America/New_York") -> Optional[datetime]:
    """
    Parse Spanish date/time expressions to datetime objects
    
    Examples:
    - "mañana a las 3pm" -> tomorrow at 3pm
    - "el martes a las 2pm" -> next Tuesday at 2pm
    - "pasado mañana a las 10am" -> day after tomorrow at 10am
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    text_lower = text.lower().strip()
    
    # Extract time
    time_hour = None
    time_period = None
    
    # Look for time patterns
    import re
    time_match = re.search(r'(\d{1,2})\s*(am|pm)', text_lower)
    if time_match:
        time_hour = int(time_match.group(1))
        time_period = time_match.group(2)
        
        if time_period == 'pm' and time_hour != 12:
            time_hour += 12
        elif time_period == 'am' and time_hour == 12:
            time_hour = 0
    
    # Determine the date
    target_date = None
    
    if 'mañana' in text_lower:
        if 'pasado' in text_lower:
            # Day after tomorrow
            target_date = now + timedelta(days=2)
        else:
            # Tomorrow
            target_date = now + timedelta(days=1)
    
    elif any(day in text_lower for day in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']):
        # Next occurrence of specified day
        days_spanish = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 
            'jueves': 3, 'viernes': 4, 'sábado': 5, 'domingo': 6
        }
        
        for day_name, day_num in days_spanish.items():
            if day_name in text_lower:
                days_ahead = (day_num - now.weekday()) % 7
                if days_ahead == 0:  # If it's the same day, assume next week
                    days_ahead = 7
                target_date = now + timedelta(days=days_ahead)
                break
    
    elif 'hoy' in text_lower or 'ahora' in text_lower:
        # Today
        target_date = now
    
    # Combine date and time
    if target_date and time_hour is not None:
        result = target_date.replace(
            hour=time_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        logger.info(f"Parsed '{text}' to {result}")
        return result
    
    return None


def generate_available_slots(
    num_slots: int = 3,
    start_hour: int = 9,
    end_hour: int = 18,
    timezone: str = "America/New_York"
) -> List[Dict[str, Any]]:
    """
    Generate available appointment slots for the next few days
    
    Args:
        num_slots: Number of slots to generate
        start_hour: Business start hour (24h format)
        end_hour: Business end hour (24h format)
        timezone: Timezone for slots
        
    Returns:
        List of available slots with start/end times
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    slots = []
    
    # Start from tomorrow
    current_date = now + timedelta(days=1)
    current_date = current_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    days_checked = 0
    while len(slots) < num_slots and days_checked < 7:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            # Morning slot (10am)
            morning_slot = current_date.replace(hour=10)
            if morning_slot > now:
                slots.append({
                    "startTime": morning_slot,
                    "endTime": morning_slot + timedelta(hours=1),
                    "available": True
                })
            
            # Afternoon slot (2pm)
            if len(slots) < num_slots:
                afternoon_slot = current_date.replace(hour=14)
                if afternoon_slot > now:
                    slots.append({
                        "startTime": afternoon_slot,
                        "endTime": afternoon_slot + timedelta(hours=1),
                        "available": True
                    })
            
            # Late afternoon slot (4pm)
            if len(slots) < num_slots:
                late_slot = current_date.replace(hour=16)
                if late_slot > now:
                    slots.append({
                        "startTime": late_slot,
                        "endTime": late_slot + timedelta(hours=1),
                        "available": True
                    })
        
        # Move to next day
        current_date += timedelta(days=1)
        days_checked += 1
    
    return slots[:num_slots]


def format_slot_for_spanish(slot: Dict[str, Any]) -> str:
    """
    Format a slot for Spanish conversation
    
    Example: "martes a las 2pm"
    """
    start_time = slot["startTime"]
    
    # Day names in Spanish
    days_spanish = {
        0: "lunes", 1: "martes", 2: "miércoles",
        3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"
    }
    
    # Get day name
    day_name = days_spanish[start_time.weekday()]
    
    # Format time
    hour = start_time.hour
    if hour == 0:
        time_str = "12am"
    elif hour < 12:
        time_str = f"{hour}am"
    elif hour == 12:
        time_str = "12pm"
    else:
        time_str = f"{hour-12}pm"
    
    # Check if it's tomorrow
    now = datetime.now(start_time.tzinfo)
    if (start_time.date() - now.date()).days == 1:
        return f"mañana a las {time_str}"
    else:
        return f"el {day_name} a las {time_str}"


def format_slots_for_customer(slots: List[Dict[str, Any]], language: str = "es") -> str:
    """
    Format available slots for customer presentation
    
    Returns a string like: "Tengo disponible mañana a las 10am o el martes a las 2pm"
    """
    if not slots:
        if language == "es":
            return "No tengo horarios disponibles esta semana."
        else:
            return "I don't have any available times this week."
    
    formatted_slots = []
    for slot in slots[:2]:  # Show max 2 options
        if language == "es":
            formatted_slots.append(format_slot_for_spanish(slot))
        else:
            # English formatting
            start = slot["startTime"]
            formatted_slots.append(start.strftime("%A at %I:%M%p").replace(" 0", " "))
    
    if language == "es":
        if len(formatted_slots) == 1:
            return f"Tengo disponible {formatted_slots[0]}"
        else:
            return f"Tengo disponible {' o '.join(formatted_slots)}"
    else:
        if len(formatted_slots) == 1:
            return f"I have {formatted_slots[0]} available"
        else:
            return f"I have {' or '.join(formatted_slots)} available"


def find_matching_slot(
    slots: List[Dict[str, Any]], 
    customer_preference: str
) -> Optional[Dict[str, Any]]:
    """
    Find a slot matching customer's preference
    
    Args:
        slots: Available slots
        customer_preference: Customer's stated preference (e.g., "mañana a las 3pm")
        
    Returns:
        Matching slot or None
    """
    # Parse customer preference
    preferred_time = parse_spanish_datetime(customer_preference)
    if not preferred_time:
        # If we can't parse, return first available slot
        return slots[0] if slots else None
    
    # Find closest matching slot
    best_match = None
    min_diff = timedelta(days=365)  # Large initial value
    
    for slot in slots:
        slot_start = slot["startTime"]
        diff = abs(slot_start - preferred_time)
        
        # If exact match or within same day
        if diff < timedelta(hours=4):
            return slot
        
        # Track closest match
        if diff < min_diff:
            min_diff = diff
            best_match = slot
    
    return best_match