"""
Parallel Tool Execution for LangGraph Agents
Enables concurrent execution of multiple operations
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from app.tools.ghl_client import ghl_client
from app.state.conversation_state import ConversationState
from app.utils.simple_logger import get_logger

logger = get_logger("parallel_tools")


@tool
async def parallel_lead_check(
    contact_id: str,
    state: InjectedState[ConversationState]
) -> Dict[str, Any]:
    """
    Check multiple lead qualification factors in parallel.
    Runs calendar, contact details, and business verification simultaneously.
    """
    logger.info(f"Running parallel checks for contact {contact_id}")
    
    try:
        # Define all checks to run in parallel
        results = await asyncio.gather(
            # Check 1: Calendar availability
            _check_calendar_availability(),
            
            # Check 2: Contact details validation
            ghl_client.get_contact(contact_id),
            
            # Check 3: Business verification (custom fields)
            ghl_client.get_contact_custom_fields(contact_id),
            
            # Return exceptions instead of failing
            return_exceptions=True
        )
        
        # Process results
        calendar_slots, contact_info, custom_fields = results
        
        # Handle any errors
        if isinstance(calendar_slots, Exception):
            logger.error(f"Calendar check failed: {calendar_slots}")
            calendar_slots = []
            
        if isinstance(contact_info, Exception):
            logger.error(f"Contact check failed: {contact_info}")
            contact_info = {}
            
        if isinstance(custom_fields, Exception):
            logger.error(f"Custom fields check failed: {custom_fields}")
            custom_fields = {}
        
        # Compile results
        return {
            "calendar_available": len(calendar_slots) > 0,
            "available_slots": calendar_slots[:3] if calendar_slots else [],
            "contact_verified": bool(contact_info.get("email")),
            "business_type": custom_fields.get("business_type", "unknown"),
            "budget_confirmed": custom_fields.get("budget", "").startswith("300"),
            "qualification_complete": all([
                len(calendar_slots) > 0,
                contact_info.get("email"),
                custom_fields.get("business_type"),
                custom_fields.get("budget")
            ])
        }
        
    except Exception as e:
        logger.error(f"Parallel lead check failed: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "qualification_complete": False
        }


async def _check_calendar_availability() -> List[Dict[str, Any]]:
    """Internal helper to check calendar slots"""
    try:
        # Get next 7 days of availability
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        # This would normally call GHL calendar API
        # For now, generate sample slots
        slots = []
        current = start_date.replace(hour=10, minute=0, second=0)
        
        for _ in range(5):  # 5 available slots
            if current.weekday() < 5:  # Weekdays only
                slots.append({
                    "start": current.isoformat(),
                    "end": (current + timedelta(hours=1)).isoformat(),
                    "available": True
                })
            current += timedelta(days=1)
            
        return slots
        
    except Exception as e:
        logger.error(f"Calendar check error: {e}")
        return []


@tool
async def parallel_message_analysis(
    messages: List[str],
    state: InjectedState[ConversationState]
) -> Dict[str, Any]:
    """
    Analyze multiple aspects of conversation in parallel.
    Checks sentiment, intent, and extracts key information simultaneously.
    """
    logger.info(f"Analyzing {len(messages)} messages in parallel")
    
    try:
        # Run analysis tasks in parallel
        results = await asyncio.gather(
            _analyze_sentiment(messages),
            _extract_business_info(messages),
            _detect_urgency(messages),
            _check_language(messages),
            return_exceptions=True
        )
        
        sentiment, business_info, urgency, language = results
        
        # Handle any errors
        if isinstance(sentiment, Exception):
            sentiment = "neutral"
        if isinstance(business_info, Exception):
            business_info = {}
        if isinstance(urgency, Exception):
            urgency = "normal"
        if isinstance(language, Exception):
            language = "es"
        
        return {
            "sentiment": sentiment,
            "business_info": business_info,
            "urgency_level": urgency,
            "language": language,
            "analysis_complete": True
        }
        
    except Exception as e:
        logger.error(f"Parallel analysis failed: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "analysis_complete": False
        }


async def _analyze_sentiment(messages: List[str]) -> str:
    """Analyze overall sentiment"""
    # Simple sentiment analysis
    positive_words = ["gracias", "excelente", "perfecto", "genial", "bien"]
    negative_words = ["no", "problema", "mal", "difícil", "caro"]
    
    text = " ".join(messages).lower()
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    return "neutral"


async def _extract_business_info(messages: List[str]) -> Dict[str, str]:
    """Extract business-related information"""
    import re
    
    business_info = {}
    text = " ".join(messages).lower()
    
    # Business type patterns
    business_types = [
        "restaurante", "tienda", "salón", "clínica",
        "hotel", "gym", "spa", "agencia"
    ]
    
    for biz in business_types:
        if biz in text:
            business_info["type"] = biz
            break
    
    # Employee count
    emp_match = re.search(r'(\d+)\s*empleados?', text)
    if emp_match:
        business_info["employees"] = emp_match.group(1)
    
    # Years in business
    years_match = re.search(r'(\d+)\s*años?', text)
    if years_match:
        business_info["years"] = years_match.group(1)
    
    return business_info


async def _detect_urgency(messages: List[str]) -> str:
    """Detect urgency level"""
    urgent_phrases = [
        "urgente", "ahora", "hoy", "inmediato",
        "rápido", "pronto", "ya", "emergency"
    ]
    
    text = " ".join(messages).lower()
    if any(phrase in text for phrase in urgent_phrases):
        return "high"
    return "normal"


async def _check_language(messages: List[str]) -> str:
    """Detect primary language"""
    english_words = ["hello", "yes", "no", "thanks", "please", "what", "how"]
    spanish_words = ["hola", "sí", "no", "gracias", "por favor", "qué", "cómo"]
    
    text = " ".join(messages).lower()
    eng_count = sum(1 for word in english_words if word in text)
    esp_count = sum(1 for word in spanish_words if word in text)
    
    return "en" if eng_count > esp_count else "es"


@tool
async def parallel_appointment_prep(
    contact_id: str,
    preferred_time: Optional[str] = None,
    state: InjectedState[ConversationState]
) -> Dict[str, Any]:
    """
    Prepare everything needed for appointment booking in parallel.
    Checks calendar, validates contact, and prepares confirmation message.
    """
    logger.info(f"Preparing appointment for {contact_id}")
    
    try:
        # Run all preparation tasks in parallel
        results = await asyncio.gather(
            # Get calendar slots
            _check_calendar_availability(),
            
            # Validate contact has required info
            ghl_client.get_contact(contact_id),
            
            # Generate meeting link
            _generate_meeting_link(),
            
            # Prepare confirmation template
            _prepare_confirmation_template(contact_id),
            
            return_exceptions=True
        )
        
        slots, contact, meeting_link, template = results
        
        # Handle errors
        if isinstance(slots, Exception):
            slots = []
        if isinstance(contact, Exception):
            contact = {}
        if isinstance(meeting_link, Exception):
            meeting_link = "https://meet.google.com/abc-defg-hij"
        if isinstance(template, Exception):
            template = "Appointment confirmed!"
        
        # Find best matching slot if preferred time given
        selected_slot = None
        if preferred_time and slots:
            # Logic to match preferred time to available slots
            selected_slot = slots[0]  # Simplified - take first slot
        
        return {
            "ready_to_book": all([
                len(slots) > 0,
                contact.get("email"),
                contact.get("firstName")
            ]),
            "selected_slot": selected_slot,
            "available_slots": slots[:3],
            "meeting_link": meeting_link,
            "confirmation_template": template,
            "contact_email": contact.get("email", "")
        }
        
    except Exception as e:
        logger.error(f"Parallel appointment prep failed: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "ready_to_book": False
        }


async def _generate_meeting_link() -> str:
    """Generate or retrieve meeting link"""
    # This would integrate with Google Meet or Zoom API
    # For now, return sample link
    return f"https://meet.google.com/abc-{datetime.now().strftime('%m%d')}-xyz"


async def _prepare_confirmation_template(contact_id: str) -> str:
    """Prepare personalized confirmation message"""
    # This would load templates and personalize
    return """¡Perfecto! Tu consulta está confirmada:
📅 Fecha: {date}
⏰ Hora: {time}
💻 Link: {meeting_link}
    
¡Nos vemos pronto! 🚀"""


# Export all tools
__all__ = [
    "parallel_lead_check",
    "parallel_message_analysis", 
    "parallel_appointment_prep"
]