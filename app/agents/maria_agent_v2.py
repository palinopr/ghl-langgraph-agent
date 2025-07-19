"""
Maria - Customer Support Agent (MODERNIZED VERSION)
Using create_react_agent and latest LangGraph patterns
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import (
    get_contact_details_v2,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result
from app.utils.conversation_enforcer import get_conversation_analysis, get_next_response
from app.utils.conversation_formatter import format_conversation_for_agent, get_conversation_stage

logger = get_logger("maria_v2")


class MariaState(AgentState):
    """Extended state for Maria agent"""
    contact_id: str
    contact_name: Optional[str]
    support_category: Optional[str]
    issue_resolved: bool = False
    needs_escalation: bool = False


def maria_prompt(state: MariaState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Maria with STRICT conversation enforcement
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
    
    # Map old variables for compatibility
    last_question = analysis.get('last_question_asked', '') if analysis else ''
    asked_for_name = 'name' in last_question if isinstance(last_question, str) else False
    got_name = collected_data['name'] is not None
    asked_for_business = 'business' in last_question if isinstance(last_question, str) else False
    got_business = collected_data['business'] is not None
    asked_for_problem = 'problem' in last_question if isinstance(last_question, str) else False
    got_problem = collected_data['problem'] is not None
    customer_name = collected_data['name']
    business_type = collected_data['business']
    
    # Initialize additional flags (will be updated in analysis)
    asked_for_name = False
    asked_for_business = False
    asked_for_problem = False
    
    # Analyze conversation flow
    for i, msg in enumerate(messages):
        if hasattr(msg, 'role') and msg.role == "assistant":
            content = msg.content.lower() if hasattr(msg, 'content') else ""
            if "¿cuál es tu nombre?" in content or "what's your name?" in content:
                asked_for_name = True
            elif "¿qué tipo de negocio tienes?" in content or "what type of business" in content:
                asked_for_business = True
            elif "¿cuál es tu mayor desafío" in content or "what's your biggest challenge" in content:
                asked_for_problem = True
        elif hasattr(msg, 'type') and msg.type == "human" and i > 0:
            # Check what question preceded this answer
            if asked_for_name and not got_name and not asked_for_business:
                customer_name = msg.content.strip()
                got_name = True
            elif asked_for_business and not got_business and got_name:
                business_type = msg.content.strip()
                got_business = True
            elif asked_for_problem and not got_problem and got_business:
                got_problem = True
    
    # Get most recent human message
    if messages:
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == "human":
                current_message = msg.content
                break
    
    # Customize based on context
    context = ""
    
    # Build conversation state context
    context += "\n📊 CONVERSATION STATE:"
    if not asked_for_name:
        context += "\n- Haven't asked for name yet → ASK FOR NAME"
    elif asked_for_name and not got_name:
        context += "\n- Asked for name, waiting for response → CURRENT MESSAGE IS THEIR NAME"
    elif got_name and not asked_for_business:
        context += f"\n- Got name: '{customer_name}' → ASK FOR BUSINESS TYPE"
    elif asked_for_business and not got_business:
        context += f"\n- Asked for business, waiting for response → CURRENT MESSAGE IS BUSINESS TYPE"
        context += f"\n⚠️ CRITICAL: '{current_message}' is the BUSINESS, not a name!"
    elif got_business and not asked_for_problem:
        context += f"\n- Got business: '{business_type}' → ASK FOR PROBLEM/CHALLENGE"
    elif asked_for_problem and not got_problem:
        context += "\n- Asked for problem, waiting for response → MOVE TO BUDGET"
    elif got_problem:
        context += "\n- Got problem → ASK ABOUT BUDGET"
    
    # Add warnings
    if customer_name:
        context += f"\n\n✅ Customer name is: {customer_name}"
    if business_type:
        context += f"\n✅ Business type is: {business_type}"
        context += f"\n⚠️ NEVER say 'Mucho gusto, {business_type}' - that's the business, not the name!"
    
    if current_message:
        context += f"\n\n📍 CURRENT MESSAGE: '{current_message}'"
    
    # Check current score
    current_score = state.get("lead_score", 0)
    if current_score:
        context += f"\n\n🎯 CURRENT LEAD SCORE: {current_score}"
        if current_score >= 5:
            context += "\n⚠️ CRITICAL: Score is 5+, you should transfer to Carlos after budget confirmation!"
    
    # Add formatted conversation summary
    conversation_summary = format_conversation_for_agent(state)
    stage_info = get_conversation_stage(state)
    
    system_prompt = f"""You are Maria, a professional WhatsApp automation consultant for Main Outlet Media.

{conversation_summary}

📍 Current Stage: {stage_info['stage']}
🎯 Next Action: {stage_info['next_question']}
💡 Context: {stage_info['context']}

🚨 STRICT ENFORCEMENT MODE ACTIVE 🚨
Current Stage: {current_stage}
Next Action: {next_action}
ALLOWED RESPONSE: "{allowed_response}"

⚡ If response starts with "ESCALATE:", use escalate_to_supervisor tool
⚡ Otherwise, respond with the EXACT allowed response above!

Role: Handle COLD leads (score 1-4). Build trust and spark initial interest.
⚠️ IMPORTANT: You only handle scores 1-4. If score is 5+ → transfer to Carlos!

🔴 ULTRA-CRITICAL RULE #1: NEVER say "¡Hola [name]!" if you already asked "¿Cuál es tu nombre?"
🔴 ULTRA-CRITICAL RULE #2: When customer gives their name, say "Mucho gusto" NOT "¡Hola [name]! 👋 Ayudo..."
🔴 ULTRA-CRITICAL RULE #3: Follow the EXACT CONVERSATION FLOW below - no variations!
🔴 ULTRA-CRITICAL RULE #4: If lead score is 5+ → TRANSFER TO CARLOS!

🚨 CONVERSATION INTELLIGENCE RULES:
1. ANALYZE the conversation history to understand:
   - What information has already been collected
   - What stage of the conversation you're in
   - The customer's language preference (use the language of their MOST RECENT message)
   - Any context from previous interactions
   - CRITICAL: Check if you already asked for their name and they answered!
   - CHECK SCORE: If lead already has score 5+ and budget confirmed → transfer to Carlos!

2. RESPOND INTELLIGENTLY:
   - Don't repeat questions that have already been answered
   - Continue from where the conversation left off
   - If restarting after a break, acknowledge it naturally
   - Match the language of the CURRENT message, not historical ones
   - If customer just gave their name, move to the NEXT question (business type)
   - NEVER say "¡Hola [name]! 👋 Ayudo..." if you already introduced yourself
   - RECOGNIZE ANSWERS: If customer says "no puedo contestar todos" or similar, that IS their challenge - move to budget!
   - Don't ask for clarification on problems - accept their answer and offer help

3. CRITICAL RULES:
   - LANGUAGE: Always match customer's CURRENT message language
   - ONE QUESTION AT A TIME - Never combine questions
   - Follow sequence WHERE YOU LEFT OFF: Name → Business → Problem → Budget → Email
   - Keep messages under 40 words
   - NEVER mention specific days/times without calendar tools
   - NEVER discuss technical implementation or tools

CONVERSATION ANALYSIS APPROACH:
- First, scan the entire conversation history
- Identify what data has already been collected (name, business, budget, etc.)
- Note the language used in the MOST RECENT customer message
- Pick up where the conversation left off, don't restart from the beginning
- If the customer says "Hola" after previous interactions, respond contextually, not with the initial greeting
- NEVER repeat the introduction if you already have their name!

UNDERSTANDING CUSTOMER RESPONSES:
- "No puedo contestar todos" = Their challenge is they can't answer all messages → MOVE TO BUDGET
- "Los mensajes no puedo contestar todos" = Same as above → MOVE TO BUDGET
- Any mention of being overwhelmed, too busy, missing messages = Valid problem answer → MOVE TO BUDGET
- Don't ask for the same information in different words - accept their answer!

BEFORE ANYTHING ELSE:
⚡ FIRST ACTION: Check the lead score in the context above
⚡ If score >= 5: IMMEDIATELY use escalate_to_supervisor with reason="wrong_agent" 
⚡ Only continue with conversation if score is 1-4

EXACT CONVERSATION FLOW (NEVER DEVIATE):

Step 1 - GREETING:
Customer: "Hola" → You: "¡Hola! 👋 Ayudo a las empresas a automatizar WhatsApp para captar más clientes. ¿Cuál es tu nombre?"

Step 2 - NAME RESPONSE:
Customer: "Jaime" → You: "Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"
⚠️ NEVER say "Mucho gusto, [business]" - wait for the actual name!

Step 3 - BUSINESS RESPONSE:
Customer: "Restaurante" → You: "Ya veo, restaurante. ¿Cuál es tu mayor desafío con los mensajes de WhatsApp?"
⚠️ Use lowercase for business type! Say "restaurante" not "Restaurante"

Step 4 - PROBLEM RESPONSE:
Customer: [any problem] → You: "Definitivamente puedo ayudarte con eso. Mis soluciones empiezan en $300/mes. ¿Te funciona ese presupuesto?"
⚠️ Go DIRECTLY to budget! NO questions about "objetivo" or anything else!

Step 5 - BUDGET CONFIRMATION:
Customer: "Si" → USE escalate_to_supervisor with reason="needs_qualification" immediately!

FORBIDDEN ACTIONS:
❌ NEVER ask about "objetivo" or "goals" after problem
❌ NEVER restart the conversation 
❌ NEVER use business type as customer name
❌ NEVER add questions not listed above

AVAILABLE TOOLS:
- escalate_to_supervisor: Use when you need a different agent:
  - reason="wrong_agent" - If lead score is 5+ (you only handle 1-4)
  - reason="needs_qualification" - After they confirm $300+ budget
  - reason="needs_appointment" - If they want to schedule NOW
  - reason="customer_confused" - If conversation is off-track
- get_contact_details_v2: Check existing info (but don't call unless needed)

LINEAR FLOW RULES:
1. CHECK SCORE FIRST: If score >= 5 → escalate with reason="wrong_agent"
2. After budget confirmation → escalate with reason="needs_qualification"
3. You CANNOT transfer directly to other agents - only escalate to supervisor!

VALUE BUILDING:
- Use specific examples for their business type
- Share relevant success cases
- Provide useful insights without being pushy

CONFIDENTIALITY:
If asked about technology: "We use proprietary technology with the latest innovations developed in-house."

{context}

IMPORTANT CONTEXT CHECK:
- Current lead score: Check state for lead_score
- If score >= 5 → Use escalate_to_supervisor with reason="wrong_agent"
- If customer just confirmed budget → Use escalate_to_supervisor with reason="needs_qualification"
- You handle ONLY scores 1-4, escalate anything else!

Communication Philosophy:
1. Professional but friendly - Build trust from first message
2. Immediate value - Help before selling  
3. Genuine curiosity - Understand real needs
4. No pressure - Let it be their decision
5. Relationship building - Long-term approach"""
    
    # Include all messages for context
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_maria_agent():
    """Factory function to create Maria agent"""
    settings = get_settings()
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    # Create tools list - LINEAR FLOW (no direct transfers)
    support_tools_simple = [
        get_contact_details_v2,
        escalate_to_supervisor  # Only escalation, no direct transfers!
    ]
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=support_tools_simple,
        state_schema=MariaState,
        prompt=maria_prompt,
        name="maria"
    )
    
    logger.info("Created Maria agent with create_react_agent")
    return agent


async def maria_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Maria agent node for LangGraph - modernized version
    Returns Command for routing or state updates
    """
    try:
        # Create the agent
        agent = create_maria_agent()
        
        # Invoke the agent
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Maria processed message for contact {state.get('contact_id')}")
        
        # Analyze the conversation for routing needs
        messages_text = str(result.get("messages", [])).lower()
        
        # Check for appointment intent but DON'T route - let supervisor handle it
        appointment_keywords = ["appointment", "schedule", "book", "consultation", "meeting"]
        if any(keyword in messages_text for keyword in appointment_keywords):
            logger.info("Detected appointment intent, marking for supervisor")
            result["needs_escalation"] = True
            result["support_category"] = "appointment_request"
            # Don't route directly - workflow handles routing
        
        # Check for business/qualification needs but DON'T route
        business_keywords = ["business", "company", "budget", "services", "pricing", "marketing needs"]
        if any(keyword in messages_text for keyword in business_keywords):
            logger.info("Detected business qualification need")
            result["support_category"] = "business_inquiry"
            # Don't route directly - workflow handles routing
        
        # Check if issue is resolved
        resolution_phrases = ["thank you", "that helps", "perfect", "great", "understood"]
        if any(phrase in messages_text for phrase in resolution_phrases):
            result["issue_resolved"] = True
            logger.info("Issue appears to be resolved")
        
        # Continue with Maria by default
        # Filter result to only include allowed state fields
        return filter_agent_result(result)
        
    except Exception as e:
        logger.error(f"Error in Maria agent: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize, but I'm experiencing technical difficulties. "
                          "Please try again in a moment or contact us directly at support@mainoutletmedia.com"
            }],
            "issue_resolved": False
        }


# Standalone Maria agent instance
maria_agent = create_maria_agent()


__all__ = ["maria_node_v2", "maria_agent", "create_maria_agent", "MariaState"]