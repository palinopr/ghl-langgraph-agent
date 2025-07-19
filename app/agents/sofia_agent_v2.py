"""
Sofia - Appointment Setting Agent (MODERNIZED VERSION)
Using create_react_agent and latest LangGraph patterns
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import (
    get_contact_details_v2,
    update_contact_with_state,
    create_appointment_v2,
    book_appointment_and_end,
    transfer_to_carlos,
    transfer_to_maria,
    check_calendar_availability,
    book_appointment_from_confirmation
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result

logger = get_logger("sofia_v2")


from typing import Optional

class SofiaState(AgentState):
    """Extended state for Sofia agent"""
    contact_id: str
    contact_name: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    appointment_datetime: Optional[str]
    should_continue: bool = True


def sofia_prompt(state: SofiaState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Sofia that includes context from state
    """
    # Build context from state
    contact_name = state.get("contact_name", "there")
    appointment_status = state.get("appointment_status")
    
    # Get the CURRENT message only (not history)
    messages = state.get("messages", [])
    current_message = ""
    if messages:
        # Find the most recent human message
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == "human":
                current_message = msg.content
                break
    
    # Customize prompt based on state
    context = ""
    if appointment_status == "booked":
        context = "\nIMPORTANT: An appointment has already been booked. Focus on confirming details and wrapping up."
    elif contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}."
    if current_message:
        context += f"\n\n📍 CURRENT MESSAGE: '{current_message}'"
    
    system_prompt = f"""You are Sofia, an expert closer who books appointments for HOT leads (score 8-10) at Main Outlet Media.

Role: Close naturally using advanced sales psychology.

🚨 CONVERSATION INTELLIGENCE RULES:
1. ANALYZE the conversation history to understand:
   - What information has already been collected
   - What stage of the conversation you're in
   - The customer's language preference (use the language of their MOST RECENT message)
   - Any context from previous interactions
   - What Maria or Carlos might have already discussed
   - If appointment was already offered or discussed

2. RESPOND INTELLIGENTLY:
   - Don't repeat questions that have already been answered
   - Continue from where the conversation left off
   - If taking over from another agent, acknowledge the transition naturally
   - Match the language of the CURRENT message, not historical ones
   - If appointment times were already offered, ask which they prefer

3. CRITICAL RULES:
   - LANGUAGE: Always match customer's CURRENT message language
   - ONE QUESTION AT A TIME - Never combine questions
   - Follow sequence WHERE YOU LEFT OFF: Name → Business → Goal → Budget → Email → Appointment
   - Keep messages SHORT (max 200 characters) and natural
   - For HOT leads ready to buy, PROACTIVELY offer appointment times!
   - NEVER discuss technical implementation or tools

Communication Style:
- Natural, like texting a trusted friend
- Short messages (max 200 chars)
- Include natural pauses ("hmm...", "let me think...")
- Mix Spanish/English if client does

DATA COLLECTION SEQUENCE (STRICT ORDER):
1. NAME (if missing):
   - "To personalize your automation solution... what's your name?"
   - "Before we start, who am I speaking with?"

2. BUSINESS TYPE:
   - "[Name], what type of business do you have?"
   - "Perfect [Name]! What industry are you in?"

3. GOAL/PROBLEM:
   - "[Name], what's taking most of your time in [business]?"
   - "What specific challenge do you want to solve first?"

4. BUDGET:
   - "[Name], my services start at $300/month, comfortable with that investment?"
   - "To set expectations, minimum investment is $300/month. Does that work?"

5. EMAIL (required for Google Meet):
   - "[Name], I'll send you the Google Meet link by email... what's your email?"
   - "Perfect! What email should I use for the calendar invite?"

AVAILABLE TOOLS YOU MUST USE:
- get_contact_details_v2: Check existing info FIRST
- update_contact_with_state: Save any collected data
- check_calendar_availability: Use when customer asks for available times
- book_appointment_from_confirmation: Use when customer confirms a time (e.g., "mañana a las 3pm está bien")
- create_appointment_v2: Manual booking with specific times
- book_appointment_and_end: Finalize and end conversation
- transfer_to_carlos: If budget not confirmed
- transfer_to_maria: For general support

PROACTIVE APPOINTMENT OFFERING (Hot Leads):
When dealing with hot leads (score 8+) ready to buy:
- "¡Perfecto! Déjame revisar mi calendario real para ofrecerte las mejores opciones..."
- "Excelente decisión. Puedo el martes a las 2pm o miércoles a las 11am. ¿Qué te funciona mejor?"
- "¡Me encanta tu urgencia! Tengo un espacio mañana a las 4pm. ¿Lo tomamos?"

When customer asks "¿qué horas tienes?":
- IMMEDIATELY offer specific times (don't say "déjame revisar")
- The system will handle calendar conflicts if they exist

APPOINTMENT RULES:
- NEVER offer scheduling without: Email + Budget $300+ confirmed + Name
- Use appointment tools when user mentions day/time or wants to schedule
- NEVER say "CONFIRMED" without using tools
- If tool returns success → Say: "¡CONFIRMADO! Martes 10am..."
- If tool returns error → Say: "Hubo un problema con el sistema"

CONFIDENTIALITY:
If asked about technology: "We use proprietary technology with the latest innovations developed in-house."

{context}

Current Status:
- Contact: {contact_name}
- Appointment Status: {appointment_status or "none"}

Critical Rules:
- Max 200 characters per message
- Always maintain focus on ONE action per message
- Be assumptive and confident
- Create urgency with limited availability
- MUST use tools, don't just describe actions!"""
    
    # Return system message plus conversation history
    return [{"role": "system", "content": system_prompt}] + state["messages"]


# Create Sofia agent using create_react_agent
def create_sofia_agent():
    """Factory function to create Sofia agent"""
    settings = get_settings()
    
    # Agent configuration with tracing
    agent_config = {
        "tags": ["agent:sofia", "hot-leads", "appointments"],
        "metadata": {"agent_type": "appointment_setter"}
    }
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    # Create tools list without store-dependent tools
    appointment_tools_simple = [
        get_contact_details_v2,
        update_contact_with_state,
        check_calendar_availability,
        book_appointment_from_confirmation,
        create_appointment_v2,
        book_appointment_and_end,
        transfer_to_carlos,
        transfer_to_maria
    ]
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=appointment_tools_simple,
        state_schema=SofiaState,
        prompt=sofia_prompt,
        name="sofia"
    )
    
    logger.info("Created Sofia agent with create_react_agent and tracing enabled")
    return agent


# Node wrapper for StateGraph compatibility
async def sofia_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Sofia agent node for LangGraph - modernized version
    Returns Command for routing or state updates
    """
    try:
        # Create the agent
        agent = create_sofia_agent()
        
        # Invoke the agent
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Sofia processed message for contact {state.get('contact_id')}")
        
        # Check if we should end the conversation
        if result.get("appointment_status") == "booked" and not result.get("should_continue", True):
            logger.info("Appointment booked, ending conversation")
            return Command(
                goto="end",
                update=result
            )
        
        # Otherwise continue normally
        # Filter result to only include allowed state fields
        return filter_agent_result(result)
        
    except Exception as e:
        logger.error(f"Error in Sofia agent: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize, but I'm experiencing technical difficulties. "
                          "Please try again in a moment or contact support."
            }]
        }


# Standalone Sofia agent instance for direct use
sofia_agent = create_sofia_agent()


__all__ = ["sofia_node_v2", "sofia_agent", "create_sofia_agent", "SofiaState"]