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
    escalate_to_supervisor,
    check_calendar_availability,
    book_appointment_from_confirmation
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result
from app.utils.conversation_enforcer import get_conversation_analysis, get_next_response
from app.utils.conversation_formatter import format_conversation_for_agent, get_conversation_stage
from app.utils.smart_responder import get_smart_response
from app.tools.appointment_booking_simple import book_appointment_simple
from app.utils.pre_model_hooks import sofia_context_hook

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
    Dynamic prompt function for Sofia with STRICT conversation enforcement
    """
    # Get messages for analysis
    messages = state.get("messages", [])
    current_message = ""
    
    # STRICT ENFORCEMENT: Use conversation analyzer
    analysis = get_conversation_analysis(messages)
    
    # Get enforcement data
    current_stage = analysis['current_stage'].value
    next_action = analysis['next_action']
    allowed_response = analysis['allowed_response']
    collected_data = analysis['collected_data']
    
    # Map for compatibility
    customer_name = collected_data['name']
    business_type_from_conv = collected_data['business']
    got_email = collected_data['email'] is not None
    
    # Get from state
    contact_name = state.get("contact_name", customer_name or "there")
    appointment_status = state.get("appointment_status")
    
    # Use conversation enforcer data - no redundant analysis needed
    got_name = collected_data['name'] is not None
    got_business = collected_data['business'] is not None
    got_problem = collected_data['problem'] is not None
    got_budget = collected_data['budget_confirmed']
    got_email = collected_data['email'] is not None
    
    # Get most recent human message
    if messages:
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == "human":
                current_message = msg.content
                break
    
    # Build conversation state context
    context = "\n📊 CONVERSATION STATE:"
    if not got_name:
        context += "\n- Need to get name"
    elif got_name and not got_business:
        context += f"\n- Got name: '{customer_name}' → ASK FOR BUSINESS TYPE"
    elif got_business and not got_problem:
        context += f"\n- Got business: '{business_type_from_conv}' → ASK FOR GOAL"
    elif got_problem and not got_budget:
        context += "\n- Got goal → ASK ABOUT BUDGET"
    elif got_budget and not got_email:
        context += "\n- Got budget → ASK FOR EMAIL"
    elif got_email:
        context += "\n- Got email → OFFER APPOINTMENT TIMES"
    
    # Add warnings
    if customer_name:
        context += f"\n\n✅ Customer name is: {customer_name}"
    if business_type_from_conv:
        context += f"\n✅ Business type is: {business_type_from_conv}"
        context += f"\n⚠️ NEVER confuse business with name!"
    
    if appointment_status == "booked":
        context += "\n\n✅ Appointment already booked - confirm and wrap up"
    
    if current_message:
        context += f"\n\n📍 CURRENT MESSAGE: '{current_message}'"
    
    # Add formatted conversation summary
    conversation_summary = format_conversation_for_agent(state)
    stage_info = get_conversation_stage(state)
    
    # PRIORITY CHECK: If customer is asking for appointment times or selecting time, override everything
    customer_asks_times = False
    customer_selects_time = False
    
    if current_message:
        if any(word in current_message.lower() for word in ["horarios", "disponibles", "horas", "cuándo", "qué días", "qué horas", "appointment", "schedule", "available"]):
            customer_asks_times = True
            logger.info(f"🚨 CUSTOMER ASKING FOR APPOINTMENT TIMES: '{current_message}'")
        
        # Check if customer is selecting a specific time
        time_patterns = ["2pm", "10am", "11am", "4pm", "martes", "miércoles", "jueves", "primera", "segunda", "perfecto"]
        if any(pattern in current_message.lower() for pattern in time_patterns):
            # Check if last AI message offered times
            for msg in reversed(messages):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                    content = msg.content.lower() if hasattr(msg, 'content') else ""
                    if "disponibilidad" in content or "2pm" in content or "11am" in content:
                        customer_selects_time = True
                        logger.info(f"🚨 CUSTOMER SELECTING TIME: '{current_message}'")
                        break
    
    system_prompt = f"""You are Sofia, an expert closer who books appointments for HOT leads (score 8-10) at Main Outlet Media.

{conversation_summary}

📍 Current Stage: {stage_info['stage']}
🎯 Next Action: {stage_info['next_question']}
💡 Context: {stage_info['context']}

🚨 PRIORITY OVERRIDE: Customer is {
"SELECTING AN APPOINTMENT TIME!" if customer_selects_time else "asking for appointment times!"
} 🚨
{
f"USE book_appointment_simple TOOL IMMEDIATELY with customer_confirmation='{current_message}', contact_id='{state.get('contact_id', '')}', contact_name='{state.get('extracted_data', {}).get('name', '') or analysis['collected_data'].get('name', 'Cliente')}', contact_email='{state.get('extracted_data', {}).get('email', '') or analysis['collected_data'].get('email', '')}'" if customer_selects_time 
else "USE check_calendar_availability TOOL IMMEDIATELY!" if customer_asks_times 
else f'''
🚨 STRICT ENFORCEMENT MODE ACTIVE 🚨
Current Stage: {current_stage}
Next Action: {next_action}
ALLOWED RESPONSE: "{allowed_response}"

⚡ CRITICAL: You MUST use the EXACT allowed response above!
⚡ The examples below are just for guidance - use ONLY the allowed response!
⚡ If response starts with "ESCALATE:", use escalate_to_supervisor tool
⚡ If allowed response is "USE_APPOINTMENT_TOOL", use book_appointment_simple tool with:
   - customer_confirmation: The time the customer just selected (from current message)
   - contact_id: {state.get('contact_id', '')}
   - contact_name: {state.get('extracted_data', {}).get('name', '') or analysis['collected_data'].get('name', 'Cliente')}
   - contact_email: {state.get('extracted_data', {}).get('email', '') or analysis['collected_data'].get('email', '')}
⚡ Otherwise, respond with the EXACT allowed response above!'''}

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
- escalate_to_supervisor: Use when you need a different agent:
  - reason="needs_qualification" - If budget not confirmed (for Carlos)
  - reason="needs_support" - For general support (for Maria)
  - reason="wrong_agent" - If you're not the right agent
  - reason="customer_confused" - If conversation is off-track

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
        book_appointment_simple,  # Simplified version that works with SofiaState
        book_appointment_from_confirmation,
        create_appointment_v2,
        book_appointment_and_end,
        escalate_to_supervisor  # Only escalation, no direct transfers!
    ]
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=appointment_tools_simple,
        state_schema=SofiaState,
        prompt=sofia_prompt,
        pre_model_hook=sofia_context_hook,  # Add context awareness
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
        # Debug state
        logger.info(f"Sofia node called with state keys: {list(state.keys())}")
        logger.info(f"Sofia extracted_data: {state.get('extracted_data', {})}")
        logger.info(f"Sofia webhook_data: {state.get('webhook_data', {})}")
        
        # Get incoming message
        webhook_data = state.get("webhook_data", {})
        incoming_message = webhook_data.get("message", "").lower()
        
        # Check if customer is asking for appointment slots
        asks_for_slots = any(word in incoming_message for word in ["horarios", "disponibles", "horas", "cuándo"])
        confirms_appointment = incoming_message in ["sí", "si", "claro", "ok", "perfecto", "dale", "yes"]
        
        # Check last AI message for appointment context
        messages = state.get("messages", [])
        last_ai_asked_appointment = False
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                content = msg.content.lower() if hasattr(msg, 'content') else ""
                if "agendar" in content or "llamada" in content:
                    last_ai_asked_appointment = True
                    break
        
        # Skip smart responder if we need appointment tools
        # Also check for time patterns
        time_patterns = ["2pm", "10am", "11am", "4pm", "martes", "miércoles", "jueves", "primera", "segunda"]
        selecting_time = any(pattern in incoming_message for pattern in time_patterns)
        
        if asks_for_slots or (confirms_appointment and last_ai_asked_appointment) or selecting_time:
            logger.info("Skipping smart responder - appointment tools needed")
            logger.info(f"  asks_for_slots: {asks_for_slots}")
            logger.info(f"  confirms_appointment: {confirms_appointment}")
            logger.info(f"  last_ai_asked_appointment: {last_ai_asked_appointment}")
            logger.info(f"  selecting_time: {selecting_time}")
            # Continue to agent
        else:
            # Check if we should use smart response
            smart_response = get_smart_response(state, "sofia")
            logger.info(f"Smart response result: {smart_response}")
            
            if smart_response:
                logger.info(f"Using smart response for Sofia: {smart_response[:50]}...")
                # Add the smart response as a message
                from langchain_core.messages import AIMessage
                return {
                    "messages": [AIMessage(content=smart_response, name="sofia")]
                }
        
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