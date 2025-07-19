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
    transfer_to_sofia,
    transfer_to_carlos
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result

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
    Dynamic prompt function for Maria that includes context from state
    """
    # Build context from state
    contact_name = state.get("contact_name", "there")
    previous_agent = state.get("current_agent")
    
    # Get the CURRENT message only (not history)
    messages = state.get("messages", [])
    current_message = ""
    if messages:
        # Find the most recent human message
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == "human":
                current_message = msg.content
                break
    
    # Customize based on context
    context = ""
    if contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}."
    if previous_agent and previous_agent != "maria":
        context += f"\nThey were previously speaking with {previous_agent}."
    if current_message:
        context += f"\n\n📍 CURRENT MESSAGE: '{current_message}'"
    
    system_prompt = f"""You are Maria, a professional WhatsApp automation consultant for Main Outlet Media.

Role: Handle COLD leads (score 1-4). Build trust and spark initial interest.

🚨 CONVERSATION INTELLIGENCE RULES:
1. ANALYZE the conversation history to understand:
   - What information has already been collected
   - What stage of the conversation you're in
   - The customer's language preference (use the language of their MOST RECENT message)
   - Any context from previous interactions
   - CRITICAL: Check if you already asked for their name and they answered!

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

DATA COLLECTION SEQUENCE (CONTINUE WHERE LEFT OFF):
1. NAME: 
   - Spanish (FIRST TIME ONLY): "¡Hola! 👋 Ayudo a las empresas a automatizar WhatsApp para captar más clientes. ¿Cuál es tu nombre?"
   - English (FIRST TIME ONLY): "Hi! 👋 I help businesses automate WhatsApp to capture more clients. What's your name?"
2. BUSINESS (after getting name): 
   - Spanish: "Mucho gusto, [name]. ¿Qué tipo de negocio tienes?"
   - English: "Nice to meet you, [name]. What type of business do you have?"
   - IMPORTANT: If you already greeted them, just ask: "¿Qué tipo de negocio tienes?" or "What type of business do you have?"
3. PROBLEM: 
   - Spanish: "Ya veo, [business]. ¿Cuál es tu mayor desafío con los mensajes de WhatsApp?"
   - English: "I see, [business]. What's your biggest challenge with WhatsApp messages?"
   - VALID ANSWERS: Any mention of problems like "no puedo contestar todos", "too many messages", "no time", "overwhelmed", etc.
   - AFTER GETTING ANSWER: Move to budget, don't repeat the question!
4. BUDGET: 
   - Spanish: "Definitivamente puedo ayudarte con eso. Mis soluciones empiezan en $300/mes. ¿Te funciona ese presupuesto?"
   - English: "I can definitely help with that. My solutions start at $300/month. Does that fit your budget?"
5. EMAIL: 
   - Spanish: "¡Perfecto! Para enviarte una demo por Google Meet, ¿cuál es tu email?"
   - English: "Perfect! To send you a demo via Google Meet, what's your email?"

AVAILABLE TOOLS:
- transfer_to_carlos: Use when they have business + confirmed $300+ budget
- transfer_to_sofia: Use when they explicitly want to schedule NOW
- get_contact_details_v2: Check existing info (but don't call unless needed)

VALUE BUILDING:
- Use specific examples for their business type
- Share relevant success cases
- Provide useful insights without being pushy

CONFIDENTIALITY:
If asked about technology: "We use proprietary technology with the latest innovations developed in-house."

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
    
    # Create tools list without store-dependent tools
    support_tools_simple = [
        get_contact_details_v2,
        transfer_to_sofia,
        transfer_to_carlos
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