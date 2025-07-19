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
    
    # Initialize flags
    asked_for_name = False
    asked_for_business = False  
    asked_for_problem = False
    asked_for_budget = False
    asked_for_email = False
    got_name = collected_data['name'] is not None
    got_business = collected_data['business'] is not None
    got_problem = collected_data['problem'] is not None
    got_budget = collected_data['budget_confirmed']
    
    # Analyze conversation flow
    for i, msg in enumerate(messages):
        if hasattr(msg, 'role') and msg.role == "assistant":
            content = msg.content.lower() if hasattr(msg, 'content') else ""
            if "¿cuál es tu nombre?" in content or "what's your name?" in content:
                asked_for_name = True
            elif "¿qué tipo de negocio" in content or "what type of business" in content:
                asked_for_business = True
            elif "¿cuál es tu mayor desafío" in content or "biggest challenge" in content or "what's taking most" in content:
                asked_for_problem = True
            elif "$" in content and ("presupuesto" in content or "budget" in content or "investment" in content):
                asked_for_budget = True
            elif "email" in content or "correo" in content:
                asked_for_email = True
        elif hasattr(msg, 'type') and msg.type == "human" and i > 0:
            # Check what question preceded this answer
            if asked_for_name and not got_name and not asked_for_business:
                customer_name = msg.content.strip()
                got_name = True
            elif asked_for_business and not got_business and got_name:
                business_type_from_conv = msg.content.strip()
                got_business = True
            elif asked_for_problem and not got_problem:
                got_problem = True
            elif asked_for_budget and not got_budget:
                if msg.content.lower() in ["si", "sí", "yes", "claro", "ok", "perfecto"]:
                    got_budget = True
            elif asked_for_email and not got_email:
                if "@" in msg.content:
                    got_email = True
    
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
    
    system_prompt = f"""You are Sofia, an expert closer who books appointments for HOT leads (score 8-10) at Main Outlet Media.

🚨 STRICT ENFORCEMENT MODE ACTIVE 🚨
Current Stage: {current_stage}
Next Action: {next_action}
ALLOWED RESPONSE: "{allowed_response}"

⚡ If response starts with "ESCALATE:", use escalate_to_supervisor tool
⚡ Otherwise, respond with the EXACT allowed response above!

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