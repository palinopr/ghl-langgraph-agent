"""
Maria - Memory-Aware Customer Support Agent
Uses isolated memory context to prevent confusion
"""
from typing import Dict, Any, List, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.tools.agent_tools_v2 import get_contact_details_v2, escalate_to_supervisor
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result
from app.utils.memory_manager import get_memory_manager
from app.utils.context_filter import ContextFilter

logger = get_logger("maria_memory_aware")


def maria_memory_prompt(state: Dict[str, Any]) -> List[AnyMessage]:
    """
    Create Maria's prompt with ISOLATED memory context
    No more confusion from other agents or historical messages!
    """
    # Get memory manager
    memory_manager = get_memory_manager()
    
    # Get Maria's isolated context
    maria_context = memory_manager.get_agent_context("maria", state)
    
    # Get only current message and recent context
    messages = maria_context.get("messages", [])
    extracted_data = maria_context.get("extracted_data", {})
    handoff_info = maria_context.get("handoff_info")
    current_message = maria_context.get("current_message", "")
    
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
        
        # Get memory manager
        memory_manager = get_memory_manager()
        
        # Check if Maria should handle this
        lead_score = state.get("lead_score", 0)
        if lead_score >= 5:
            logger.info(f"Score {lead_score} too high for Maria, escalating")
            return {
                "needs_escalation": True,
                "escalation_reason": "high_score",
                "messages": state["messages"]
            }
        
        # Create agent with memory-aware prompt
        model = create_openai_model(temperature=0.0)
        tools = [get_contact_details_v2, escalate_to_supervisor]
        
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
        
        # Add Maria's response to her memory
        if result.get("messages"):
            last_message = result["messages"][-1]
            memory_manager.add_agent_message("maria", last_message)
        
        logger.info("Maria completed successfully with isolated memory")
        
        return filter_agent_result(result)
        
    except Exception as e:
        logger.error(f"Error in Maria memory-aware: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "messages": state["messages"]
        }