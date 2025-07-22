"""
Maria - Memory-Aware Customer Support Agent
Uses isolated memory context to prevent confusion
"""
from typing import Dict, Any, List, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.tools.agent_tools_modernized import (
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
    context += f"\\n- Budget: {'CONFIRMED' if extracted_data.get('budget_confirmed') else 'NOT CONFIRMED'}"
    
    # Show current score
    lead_score = state.get("lead_score", 0)
    context += f"\\n\\n🎯 LEAD SCORE: {lead_score}/10"
    if lead_score >= 5:
        context += "\\n⚠️ Score is 5+, prepare to escalate to Carlos!"
    
    # Current message
    if current_message:
        context += f"\\n\\n💬 CUSTOMER JUST SAID: '{current_message}'"
    
    # Message count (to track context size)
    context += f"\\n\\n📊 Context size: {len(messages)} messages"
    
    system_prompt = f"""You are Maria, a professional WhatsApp automation consultant for Main Outlet Media.

🧠 MEMORY-AWARE MODE ACTIVE 🧠
You now have ISOLATED memory - you only see messages relevant to YOU.
No confusion from other agents or old conversations!

{context}

Your Role: Handle COLD leads (score 0-4), build trust, qualify initially.

CONVERSATION FLOW:
1. If no name → Ask for name
2. If no business → Ask for business type  
3. If no problem → Ask about WhatsApp challenges
4. If score < 5 → Present value and ask budget
5. If budget confirmed & score >= 5 → Escalate to Carlos

⚡ CRITICAL RULES:
- You handle scores 0-4 ONLY
- Score 5+ → Use escalate_to_supervisor tool immediately
- Speak Spanish (Mexican friendly style)
- One question at a time
- If customer provides info, acknowledge it and move forward

Remember: You have CLEAN context now - no more confusion!"""
    
    return [{"role": "system", "content": system_prompt}] + messages


async def maria_memory_aware_node(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
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