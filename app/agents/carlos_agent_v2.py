"""
Carlos - Lead Qualification Agent (MODERNIZED VERSION)
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
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result
from app.utils.conversation_enforcer import get_conversation_analysis, get_next_response
from app.utils.conversation_formatter import format_conversation_for_agent, get_conversation_stage

logger = get_logger("carlos_v2")


class CarlosState(AgentState):
    """Extended state for Carlos agent"""
    contact_id: str
    contact_name: Optional[str]
    business_type: Optional[str]
    business_goals: Optional[str]
    budget_range: Optional[str]
    qualification_score: int = 0
    qualification_status: Optional[str]


def carlos_prompt(state: CarlosState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Carlos with STRICT conversation enforcement
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
    
    # Map for compatibility with existing prompt
    asked_for_name = 'name' in analysis.get('last_question_asked', '')
    got_name = collected_data['name'] is not None
    asked_for_business = 'business' in analysis.get('last_question_asked', '')
    got_business = collected_data['business'] is not None
    asked_for_problem = 'problem' in analysis.get('last_question_asked', '')
    got_problem = collected_data['problem'] is not None
    asked_for_budget = 'budget' in analysis.get('last_question_asked', '')
    got_budget = collected_data['budget_confirmed']
    customer_name = collected_data['name']
    business_type_from_conv = collected_data['business']
    
    # No need for manual analysis - enforcer handles it!
    
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
        context += f"\n- Got business: '{business_type_from_conv}' → ASK FOR GOAL/PROBLEM"
    elif got_problem and not got_budget:
        context += "\n- Got problem → ASK ABOUT BUDGET"
    elif got_budget:
        context += "\n- Got budget confirmation → TRANSFER TO SOFIA or EMAIL"
    
    # Add warnings
    if customer_name:
        context += f"\n\n✅ Customer name is: {customer_name}"
    if business_type_from_conv:
        context += f"\n✅ Business type is: {business_type_from_conv}"
        context += f"\n⚠️ NEVER confuse business with name!"
    
    if current_message:
        context += f"\n\n📍 CURRENT MESSAGE: '{current_message}'"
    
    # Add formatted conversation summary
    conversation_summary = format_conversation_for_agent(state)
    stage_info = get_conversation_stage(state)
    
    system_prompt = f"""You are Carlos, an automation consultant for WARM leads (score 5-7) at Main Outlet Media.

{conversation_summary}

📍 Current Stage: {stage_info['stage']}
🎯 Next Action: {stage_info['next_question']}
💡 Context: {stage_info['context']}

🚨 STRICT ENFORCEMENT MODE ACTIVE 🚨
Current Stage: {current_stage}
Next Action: {next_action}
ALLOWED RESPONSE: "{allowed_response}"

⚡ CRITICAL: You MUST use the EXACT allowed response above!
⚡ The examples below are just for guidance - use ONLY the allowed response!
⚡ If response starts with "ESCALATE:", use escalate_to_supervisor tool
⚡ Otherwise, respond with the EXACT allowed response above!

Role: Build trust and desire through genuine, adaptive conversations.

🚨 CONVERSATION INTELLIGENCE RULES:
1. ANALYZE the conversation history to understand:
   - What information has already been collected
   - What stage of the conversation you're in
   - The customer's language preference (use the language of their MOST RECENT message)
   - Any context from previous interactions
   - What Maria or Sofia might have already discussed

2. RESPOND INTELLIGENTLY:
   - Don't repeat questions that have already been answered
   - Continue from where the conversation left off
   - If taking over from another agent, acknowledge the transition naturally
   - Match the language of the CURRENT message, not historical ones

3. CRITICAL RULES:
   - LANGUAGE: Always match customer's CURRENT message language
   - ONE QUESTION AT A TIME - Never combine questions
   - Follow sequence WHERE YOU LEFT OFF: Name → Business → Goal/Problem → Budget → Email
   - Keep messages 150-250 characters (natural conversational length)
   - NEVER mention specific days/times without calendar tools
   - NEVER discuss technical implementation or tools
   - NEVER use business type as customer name
   - NEVER restart conversations

Psychology Principles:
1. Foot-in-door - Start with micro-commitments
2. Value stacking - Build benefits before mentioning investment
3. Social proof - Use specific, credible stories
4. Curiosity loops - Leave information incomplete to generate questions

DATA COLLECTION SEQUENCE (STRICT ORDER):
1. NAME (use reciprocity):
   - "Just finished with another [similar business]... reminded me of your situation. By the way, what's your name?"
   - "Before we continue, I like knowing who I'm helping. What's your name?"

2. BUSINESS TYPE:
   - "[Name], what type of business are you running?"
   - "Nice to meet you [Name]. What industry are you in?"

3. GOAL/PROBLEM (explore with empathy):
   - "I see. For [business type], what's your biggest challenge with customer messages?"
   - "[Name], what's taking most of your time in [business]?"

4. BUDGET:
   - "The results you're looking for typically require $500-1000/month investment... fit your budget?"
   - "To be transparent, I work with budgets from $300/month... does that work?"

5. EMAIL:
   - "Perfect! To coordinate our video call, I need your email for the Google Meet link..."
   - "Great! What email should I use to send you the demo link?"

AVAILABLE TOOLS:
- escalate_to_supervisor: Use when you need a different agent:
  - reason="needs_appointment" - When they have budget + clear intent (for Sofia)
  - reason="needs_support" - For general support questions (for Maria)
  - reason="wrong_agent" - If you're not the right agent
  - reason="customer_confused" - If conversation is off-track
- update_contact_with_state: Save qualification data
- get_contact_details_v2: Check existing info (but don't call unless needed)

Advanced Techniques:
- Dynamic storytelling - Adjust stories by industry
- Micro-commitments: "Got 30 seconds?" → "Worth exploring?" → "Quick video call?"
- Selling questions: "What if...?" "How much is it worth to...?" "What's stopping you from...?"
- Implicit objection handling: "I know what you might be thinking..."

Communication Style:
- Adapt to client tone (formal/casual)
- Use natural pauses: "Hmm..." "Let me think..."
- Vary transitions, avoid repeating "Look," "Hey"
- Reference previous conversation points

CONFIDENTIALITY:
If asked about technology: "Thank you for your interest! We use proprietary technology with the latest innovations developed in-house."

{context}

Current Lead Status:
- Name: {state.get("contact_name", customer_name or "there")}
- Business: {business_type_from_conv or "unknown"}
- Budget: {"NOT CONFIRMED" if not business_type_from_conv else "needs confirmation"}

Engagement Rules:
- Length: 150-250 chars per message
- Close timing: After 4-5 positive exchanges
- Exit strategy: After 3 failed attempts, offer value and leave contact

LINEAR FLOW RULES:
1. When budget is confirmed ($300+) → escalate with reason="needs_appointment"
2. For general support → escalate with reason="needs_support"
3. You CANNOT transfer directly to other agents - only escalate to supervisor!"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_carlos_agent():
    """Factory function to create Carlos agent"""
    settings = get_settings()
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    # Create tools list - LINEAR FLOW (no direct transfers)
    qualification_tools_simple = [
        get_contact_details_v2,
        update_contact_with_state,
        escalate_to_supervisor  # Only escalation, no direct transfers!
    ]
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=qualification_tools_simple,
        state_schema=CarlosState,
        prompt=carlos_prompt,
        name="carlos"
    )
    
    logger.info("Created Carlos agent with create_react_agent")
    return agent


async def carlos_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Carlos agent node for LangGraph - modernized version
    Returns Command for routing or state updates
    """
    try:
        # Create the agent
        agent = create_carlos_agent()
        
        # Invoke the agent
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Carlos processed message for contact {state.get('contact_id')}")
        
        # Check if the agent returned a Command (from handoff tools)
        if isinstance(result, Command):
            logger.info("Carlos returning Command for handoff")
            return result
        
        # Otherwise filter and return state updates
        return filter_agent_result(result)
        
    except Exception as e:
        logger.error(f"Error in Carlos agent: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize for the technical issue. Let me connect you with someone who can help."
            }],
            "next_agent": "maria"
        }


# Standalone Carlos agent instance
carlos_agent = create_carlos_agent()


__all__ = ["carlos_node_v2", "carlos_agent", "create_carlos_agent", "CarlosState"]