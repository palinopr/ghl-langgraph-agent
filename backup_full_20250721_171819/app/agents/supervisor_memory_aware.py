"""
Memory-Aware Supervisor
Handles agent routing with proper memory handoffs
"""
from typing import Dict, Any, Optional
from app.utils.simple_logger import get_logger
from app.utils.memory_manager import get_memory_manager
from app.utils.context_filter import ContextFilter
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from langchain_core.messages import SystemMessage

logger = get_logger("supervisor_memory_aware")


async def supervisor_memory_aware_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced supervisor that manages memory during agent routing
    
    Key improvements:
    1. Prepares isolated context for routing decision
    2. Handles memory handoffs between agents
    3. Adds handoff messages for context
    """
    logger.info("=== MEMORY-AWARE SUPERVISOR STARTING ===")
    
    # Get memory manager
    memory_manager = get_memory_manager()
    
    # Get current agent (if any)
    current_agent = state.get("current_agent")
    
    # Extract key information
    lead_score = state.get("lead_score", 0)
    extracted_data = state.get("extracted_data", {})
    current_intent = state.get("current_intent", "unknown")
    
    # Get supervisor's view of the conversation
    # Use ContextFilter to get clean context
    supervisor_context = ContextFilter.prepare_agent_context(
        agent_name="supervisor",
        messages=state.get("messages", []),
        extracted_data=extracted_data,
        current_intent=current_intent,
        include_historical=False  # Supervisor doesn't need history
    )
    
    logger.info(f"Supervisor context: {supervisor_context['message_count']} messages")
    logger.info(f"Current intent: {current_intent}, Score: {lead_score}")
    
    # Determine next agent based on score and intent
    next_agent = determine_next_agent(lead_score, current_intent, extracted_data)
    
    logger.info(f"Routing decision: {current_agent} → {next_agent}")
    
    # Handle agent transition
    if current_agent and current_agent != next_agent:
        # This is a handoff
        logger.info(f"HANDOFF REQUIRED: {current_agent} → {next_agent}")
        
        # Create handoff context
        handoff_reason = get_handoff_reason(current_agent, next_agent, lead_score, current_intent)
        
        # Use memory manager to handle handoff
        handoff_data = memory_manager.handle_agent_handoff(
            from_agent=current_agent,
            to_agent=next_agent,
            state=state
        )
        
        # Create handoff message
        handoff_message = ContextFilter.create_handoff_message(
            from_agent=current_agent,
            to_agent=next_agent,
            reason=handoff_reason,
            key_facts=extracted_data
        )
        
        # Add handoff message to state
        state["messages"].append(handoff_message)
        
        # Update state with handoff info
        state.update({
            "handoff_completed": True,
            "handoff_data": handoff_data,
            "escalation_reason": handoff_reason
        })
    
    # Update state with routing decision
    state.update({
        "next_agent": next_agent,
        "current_agent": next_agent,
        "routing_complete": True,
        "supervisor_reasoning": f"Score: {lead_score}, Intent: {current_intent} → {next_agent}"
    })
    
    # Prepare context for the next agent
    next_agent_context = memory_manager.get_agent_context(next_agent, state)
    state[f"{next_agent}_context"] = next_agent_context
    
    logger.info(f"Supervisor complete: Routing to {next_agent}")
    
    return state


def determine_next_agent(
    lead_score: int, 
    current_intent: str, 
    extracted_data: Dict[str, Any]
) -> str:
    """
    Determine which agent should handle the conversation
    
    Logic:
    - Score 0-4: Maria (cold leads, initial qualification)
    - Score 5-7: Carlos (warm leads, business discussion)
    - Score 8-10: Sofia (hot leads, appointment booking)
    - Special cases based on intent
    """
    # Check for explicit appointment intent
    if current_intent == "appointment_booking":
        return "sofia"
    
    # Check if ready for appointment (all data collected)
    has_all_data = all([
        extracted_data.get("name"),
        extracted_data.get("business_type"),
        extracted_data.get("goal"),
        extracted_data.get("budget_confirmed")
    ])
    
    if has_all_data and lead_score >= 7:
        return "sofia"
    
    # Score-based routing
    if lead_score <= 4:
        return "maria"
    elif lead_score <= 7:
        return "carlos"
    else:
        return "sofia"


def get_handoff_reason(
    from_agent: str, 
    to_agent: str, 
    lead_score: int, 
    current_intent: str
) -> str:
    """Generate appropriate handoff reason"""
    
    reasons = {
        ("maria", "carlos"): f"Lead qualified (score: {lead_score}), needs business discussion",
        ("maria", "sofia"): f"High interest lead ready for appointment (score: {lead_score})",
        ("carlos", "sofia"): "Business qualified, ready to book appointment",
        ("carlos", "maria"): "Lead needs more nurturing",
        ("sofia", "carlos"): "Customer needs more information before booking",
        ("sofia", "maria"): "Customer not ready, needs qualification"
    }
    
    return reasons.get((from_agent, to_agent), f"Routing based on score {lead_score} and intent {current_intent}")