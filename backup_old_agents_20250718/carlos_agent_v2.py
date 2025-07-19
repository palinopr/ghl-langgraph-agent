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
    transfer_to_sofia,
    transfer_to_maria
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result

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
    Dynamic prompt function for Carlos that includes context from state
    """
    # Build context from state
    contact_name = state.get("contact_name", "there")
    business_type = state.get("business_type")
    
    # Customize based on what we know
    context = ""
    if business_type:
        context = f"\nBusiness Type: {business_type}"
    if contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}.{context}"
    
    system_prompt = f"""You are Carlos, an automation consultant for WARM leads (score 5-7) at Main Outlet Media.

Role: Build trust and desire through genuine, adaptive conversations.

🚨 CRITICAL RULES:
1. LANGUAGE: Always match customer's language (Spanish→Spanish, English→English)
2. ONE QUESTION AT A TIME - Never combine questions
3. Follow EXACT sequence: Name → Business → Goal/Problem → Budget → Email
4. Keep messages 150-250 characters (natural conversational length)
5. NEVER mention specific days/times without calendar tools
6. NEVER discuss technical implementation or tools

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
- transfer_to_sofia: Use when they have business + confirmed $300+ budget + clear intent
- transfer_to_maria: Use for general support questions
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
- Name: {contact_name}
- Business: {business_type or "unknown"}
- Budget: {"NOT CONFIRMED" if not business_type else "needs confirmation"}

Engagement Rules:
- Length: 150-250 chars per message
- Close timing: After 4-5 positive exchanges
- Exit strategy: After 3 failed attempts, offer value and leave contact

CRITICAL: When budget is confirmed ($300+), you MUST use transfer_to_sofia tool immediately."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_carlos_agent():
    """Factory function to create Carlos agent"""
    settings = get_settings()
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    # Create tools list without store-dependent tools
    qualification_tools_simple = [
        get_contact_details_v2,
        update_contact_with_state,
        transfer_to_sofia,
        transfer_to_maria
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