"""
Maria - Customer Support Agent (ENHANCED VERSION)
Fixed to properly use extracted_data from intelligence layer
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
from app.utils.pre_model_hooks import maria_context_hook

logger = get_logger("maria_v2_enhanced")


class MariaState(AgentState):
    """Extended state for Maria agent"""
    contact_id: str
    contact_name: Optional[str]
    support_category: Optional[str]
    issue_resolved: bool = False
    needs_escalation: bool = False


def maria_prompt(state: MariaState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Maria with ENHANCED data handling
    Prioritizes extracted_data from intelligence layer over conversation analysis
    """
    # Get messages for analysis
    messages = state.get("messages", [])
    current_message = ""
    
    # ENHANCED: Get extracted data from intelligence layer FIRST
    extracted_data = state.get("extracted_data", {})
    
    # Get conversation analysis for flow control (not data extraction)
    analysis = get_conversation_analysis(messages)
    
    # Get enforcement data
    current_stage = analysis['current_stage'].value
    next_action = analysis['next_action']
    allowed_response = analysis['allowed_response']
    
    # ENHANCED: Build data view prioritizing intelligence layer extraction
    customer_name = extracted_data.get('name')
    business_type = extracted_data.get('business_type')
    budget_info = extracted_data.get('budget')
    goal_info = extracted_data.get('goal')
    email_info = extracted_data.get('email')
    
    # Get most recent human message
    if messages:
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == "human":
                current_message = msg.content
                break
    
    # Build context showing what we ACTUALLY have
    context = "\n📊 CONVERSATION STATE:"
    context += f"\n- Current Stage: {current_stage}"
    context += f"\n- Next Action: {next_action}"
    context += f"\n- Language: {analysis.get('language', 'es').upper()}"
    
    # Show data from intelligence layer
    context += "\n\n📋 EXTRACTED DATA (from Intelligence Layer):"
    if customer_name:
        context += f"\n✅ Customer name: {customer_name}"
    else:
        context += f"\n❌ Customer name: NOT PROVIDED YET"
        
    if business_type:
        context += f"\n✅ Business type: {business_type}"
    else:
        context += f"\n❌ Business type: NOT PROVIDED YET"
        
    if goal_info:
        context += f"\n✅ Goal/Problem: {goal_info}"
    else:
        context += f"\n❌ Goal/Problem: NOT PROVIDED YET"
        
    if budget_info:
        context += f"\n✅ Budget: {budget_info}"
    else:
        context += f"\n❌ Budget: NOT CONFIRMED YET"
        
    if email_info:
        context += f"\n✅ Email: {email_info}"
    else:
        context += f"\n❌ Email: NOT PROVIDED YET"
    
    # ENHANCED: Smart response adjustment based on what we have
    if business_type and "business" in analysis.get('expecting_answer_for', ''):
        # We already have business type from extraction, skip to next question
        context += "\n\n⚡ SMART ADJUSTMENT: Business type already extracted, skip to problem question!"
        if "problema" in allowed_response or "desafío" in allowed_response:
            # Good, already asking about problem
            pass
        else:
            # Override to ask about problem instead
            allowed_response = "Ya veo, {business}. ¿Cuál es tu mayor desafío con los mensajes de WhatsApp?"
            allowed_response = allowed_response.replace("{business}", business_type)
    
    # Add allowed response
    context += f"\n\n🎯 ALLOWED RESPONSE: \"{allowed_response}\""
    
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
    
    # Check if this is a returning customer with history
    has_previous_conversation = any(
        msg.additional_kwargs.get('source') == 'ghl_history' 
        for msg in messages 
        if hasattr(msg, 'additional_kwargs')
    )
    
    system_prompt = f"""You are Maria, a professional WhatsApp automation consultant for Main Outlet Media.

{'🔄 RETURNING CUSTOMER DETECTED - Check conversation history below!' if has_previous_conversation else ''}

{conversation_summary}

📍 Current Stage: {stage_info['stage']}
🎯 Next Action: {stage_info['next_question']}
💡 Context: {stage_info['context']}

🚨 ENHANCED DATA HANDLING MODE 🚨
Always check the EXTRACTED DATA section above FIRST!
- If we already have the data, DON'T ask for it again
- Skip to the next relevant question
- Use the extracted data in your responses

⚡ CRITICAL: You MUST use the EXACT allowed response above!
⚡ EXCEPTION: If data is already extracted, adjust the response accordingly
⚡ If response starts with "ESCALATE:", use escalate_to_supervisor tool

Role: Handle COLD leads (score 1-4). Build trust and spark initial interest.
⚠️ IMPORTANT: You only handle scores 1-4. If score is 5+ → transfer to Carlos!

🔴 ULTRA-CRITICAL RULES:
1. NEVER ask for information you already have in EXTRACTED DATA
2. If customer provides business type, acknowledge it and move to next question
3. Follow the conversation flow but skip questions for data you already have
4. Always use data from EXTRACTED DATA section, not from conversation parsing

🚨 CONVERSATION INTELLIGENCE RULES:
1. USE EXTRACTED DATA:
   - The extracted_data shows what the Intelligence Layer found
   - This is MORE RELIABLE than conversation parsing
   - If business_type is in extracted_data, we HAVE IT
   
2. RESPOND INTELLIGENTLY:
   - Don't repeat questions that have been answered
   - If customer just said "Restaurante", that's their business type
   - Move to the next logical question
   - Acknowledge what they told you

BEFORE ANYTHING ELSE:
⚡ FIRST ACTION: Check the lead score in the context above
⚡ If score >= 5: IMMEDIATELY use escalate_to_supervisor with reason="wrong_agent" 
⚡ Only continue with conversation if score is 1-4

{context}

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
        pre_model_hook=maria_context_hook,  # Add context awareness
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