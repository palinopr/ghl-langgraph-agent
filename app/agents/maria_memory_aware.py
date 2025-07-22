"""
Maria - Memory-Aware Customer Support Agent
Uses isolated memory context to prevent confusion
"""
from typing import Dict, Any, List
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
# Command import removed for backward compatibility
from app.state.minimal_state import MinimalState
from app.tools.agent_tools_fixed import (
    get_contact_details_with_task,
    escalate_to_supervisor,
    update_contact_with_context,
    save_important_context
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.agents.base_agent import (
    get_current_message,
    check_score_boundaries,
    extract_data_status,
    create_error_response,
    get_base_contact_info
)

logger = get_logger("maria_memory_aware")


def maria_memory_prompt(state: Dict[str, Any]) -> List[AnyMessage]:
    """
    Create Maria's prompt with ISOLATED memory context
    No more confusion from other agents or historical messages!
    """
    # Get context directly from state (memory manager removed)
    messages = state.get("messages", [])
    extracted_data = state.get("extracted_data", {})
    handoff_info = state.get("handoff_info")
    current_message = get_current_message(messages)
    
    # Build Maria's view of the conversation
    context = "\\n📊 MARIA'S CONTEXT:\\n"
    
    # Check if this is ongoing conversation
    is_new_conversation = len(messages) <= 2  # First exchange
    has_greeted = any("hola" in str(msg.content).lower() for msg in messages[:-1] if hasattr(msg, 'name') and msg.name == 'maria')
    
    context += f"\\n🔄 CONVERSATION STATUS: {'NEW - Greet customer' if is_new_conversation and not has_greeted else 'ONGOING - NO greeting needed'}"
    
    # Show handoff if receiving one
    if handoff_info:
        context += f"\\n🔄 HANDOFF: Received from {handoff_info['from_agent']}"
        context += f"\\n   Reason: {handoff_info['reason']}"
        context += "\\n"
    
    # Show what data we have
    context += "\\n📋 CUSTOMER DATA:"
    context += f"\\n- Name: {extracted_data.get('name', 'NOT PROVIDED')}"
    context += f"\\n- Business: {extracted_data.get('business_type', 'NOT PROVIDED')}"
    context += f"\\n- Problem: {extracted_data.get('goal', 'NOT PROVIDED')}"
    context += f"\\n- Budget: {extracted_data.get('budget', 'NOT PROVIDED')}"
    
    # Show current score
    lead_score = state.get("lead_score", 0)
    context += f"\\n\\n🎯 LEAD SCORE: {lead_score}/10"
    if lead_score >= 5:
        context += "\\n⚠️ Score is 5+, prepare to escalate to Carlos!"
    
    # Current message
    if current_message:
        context += f"\\n\\n💬 CUSTOMER JUST SAID: '{current_message}'"
        # Highlight if they just provided new business info
        if "restaurante" in current_message.lower() or "restaurant" in current_message.lower():
            context += "\\n🆕 NEW BUSINESS TYPE MENTIONED!"
    
    # Message count (to track context size)
    context += f"\\n\\n📊 Context size: {len(messages)} messages"
    
    system_prompt = f"""You are Maria, a WhatsApp automation specialist for Main Outlet Media.

{context}

🎯 YOUR GOAL: Book a DEMO CALL by showing how WhatsApp automation solves their specific problem.

✅ DATA CHECK - Before asking, check what we already have:
- Name: {extracted_data.get('name', 'NOT PROVIDED')}
- Business: {extracted_data.get('business_type', 'NOT PROVIDED')}  
- Problem: {extracted_data.get('goal', 'NOT PROVIDED')}
- Budget: {extracted_data.get('budget', 'NOT PROVIDED')}

📋 CONVERSATION STRATEGY:
1. NEVER repeat greetings if conversation already started
2. NEVER ask for data we already have
3. If they state a problem → Show impact & offer solution
4. Focus on their PROBLEM, not just collecting data

💬 PROBLEM-FOCUSED FLOW:
- If they mention losing customers → "¿Cuántos clientes crees que pierdes al mes por no responder rápido?"
- If they mention being busy → "¿Cuántas horas al día pasas respondiendo mensajes?"
- Always connect to solution → "Con WhatsApp automatizado, podrías..."

🚀 DEMO BOOKING APPROACH:
- Present value based on THEIR problem
- "Te puedo mostrar exactamente cómo automatizar las respuestas para tu negocio"
- "¿Tienes 15 minutos mañana para ver una demo personalizada?"

⚡ CRITICAL RULES:
- Lead score 0-4 only (5+ → escalate immediately)
- One strategic question at a time
- Always move toward booking a demo
- Speak conversational Mexican Spanish
- If they provide new info (like business type), UPDATE your understanding

Remember: You're not just collecting data - you're solving their WhatsApp communication problem!"""
    
    return [{"role": "system", "content": system_prompt}] + messages


async def maria_memory_aware_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maria agent node with memory isolation
    """
    try:
        logger.info("=== MARIA MEMORY-AWARE STARTING ===")
        
        # Check if Maria should handle this
        lead_score = state.get("lead_score", 0)
        boundary_check = check_score_boundaries(lead_score, 0, 4, "Maria", logger)
        if boundary_check:
            return boundary_check
        
        # Create agent with memory-aware prompt
        model = create_openai_model(temperature=0.0)
        tools = [
            get_contact_details_with_task,
            escalate_to_supervisor,
            update_contact_with_context,
            save_important_context
        ]
        
        # Get memory-aware messages
        messages = maria_memory_prompt(state)
        
        # Create proper state for the agent
        agent_state = {
            "messages": messages,
            "remaining_steps": 10  # Required by create_react_agent
        }
        
        agent = create_react_agent(
            model=model,
            tools=tools,
            state_schema=MinimalState,  # Enable InjectedState support
            name="maria"
        )
        
        # Invoke agent with proper state
        result = await agent.ainvoke(agent_state)
        
        # Memory manager removed - responses handled by state
        
        logger.info("Maria completed successfully with isolated memory")
        
        return result  # filter_agent_result removed
        
    except Exception as e:
        logger.error(f"Error in Maria memory-aware: {str(e)}", exc_info=True)
        return create_error_response("maria", e, state)