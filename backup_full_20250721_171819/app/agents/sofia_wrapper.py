"""
Sofia wrapper that uses the fixed version for appointment operations
"""
from typing import Dict, Any, Union
from langgraph.types import Command
from app.agents.sofia_agent_v2 import sofia_node_v2
from app.agents.sofia_agent_v2_fixed import sofia_node_v2_fixed
from app.utils.simple_logger import get_logger

logger = get_logger("sofia_wrapper")


async def sofia_node_smart(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Smart Sofia node that uses fixed version for appointments
    """
    # Get the current message
    webhook_data = state.get("webhook_data", {})
    current_message = webhook_data.get("message", "").lower()
    
    # Check messages for appointment context
    messages = state.get("messages", [])
    
    # Check if this is appointment-related
    appointment_keywords = [
        "horarios", "disponibles", "horas", "cuándo", "cuando",
        "qué días", "que dias", "appointment", "schedule", "available",
        "agendar", "cita", "llamada", "2pm", "10am", "11am", "4pm",
        "martes", "miércoles", "jueves", "lunes", "viernes",
        "perfecto", "está bien"
    ]
    
    # Check if appointment-related
    is_appointment_related = any(kw in current_message for kw in appointment_keywords)
    
    # Also check if previous message offered appointment times
    offered_times_recently = False
    if len(messages) >= 2:
        for msg in messages[-3:]:  # Check last 3 messages
            if hasattr(msg, 'content'):
                content = str(msg.content).lower()
                if any(time in content for time in ["10:00", "2:00", "4:00", "horarios disponibles"]):
                    offered_times_recently = True
                    break
    
    # Use fixed version for appointment-related messages
    if is_appointment_related or offered_times_recently:
        logger.info("🔧 Using FIXED Sofia for appointment operation")
        return await sofia_node_v2_fixed(state)
    else:
        logger.info("Using regular Sofia")
        return await sofia_node_v2(state)


# Export the wrapper
__all__ = ["sofia_node_smart"]