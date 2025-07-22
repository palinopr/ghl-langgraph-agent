"""
Proper agent creation pattern for LangGraph 0.5.3
Shows how to create agents with state_schema for InjectedState support
"""
from typing import Dict, Any, List, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from app.state.minimal_state import MinimalState
from app.utils.model_factory import create_openai_model
from app.utils.simple_logger import get_logger

logger = get_logger("agent_pattern")


def create_agent_with_state_schema_example():
    """
    Example of creating an agent with proper state_schema
    This enables tools to use InjectedState without validation errors
    """
    
    # 1. Create the model
    model = create_openai_model(temperature=0.7)
    
    # 2. Define tools (can use InjectedState when state_schema is provided)
    from app.tools.agent_tools_fixed import (
        get_contact_details_with_task,
        escalate_to_supervisor,
        update_contact_with_context,
        save_important_context
    )
    
    tools = [
        get_contact_details_with_task,
        escalate_to_supervisor,
        update_contact_with_context,
        save_important_context
    ]
    
    # 3. Define prompt (can be static or dynamic)
    agent_prompt = """You are a helpful AI assistant for Main Outlet Media.
    
    Current state information:
    - Lead Score: {lead_score}
    - Contact ID: {contact_id}
    - Current Messages: {message_count}
    
    Use the available tools to help the customer and escalate when needed.
    """
    
    # 4. Create agent WITH state_schema - THIS IS THE KEY!
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState,  # Enables InjectedState in tools
        prompt=agent_prompt,
        name="example_agent"
    )
    
    return agent


async def agent_node_pattern(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Pattern for creating an agent node that properly handles state
    """
    try:
        # 1. Ensure required fields exist
        if "messages" not in state:
            state["messages"] = []
        if "remaining_steps" not in state:
            state["remaining_steps"] = 10  # Required by create_react_agent
        
        # 2. Create agent with state schema
        agent = create_agent_with_state_schema_example()
        
        # 3. Prepare state with any dynamic values needed by prompt
        agent_state = {
            **state,
            "lead_score": state.get("lead_score", 0),
            "contact_id": state.get("contact_id", "unknown"),
            "message_count": len(state.get("messages", []))
        }
        
        # 4. Invoke agent
        result = await agent.ainvoke(agent_state)
        
        # 5. Handle results
        # If agent returns a Command, it will be in the result
        # Otherwise, return state updates
        
        return result
        
    except Exception as e:
        logger.error(f"Error in agent: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "messages": state.get("messages", [])
        }


# Example: Maria agent with proper state_schema
async def maria_fixed_node(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Maria agent with proper state_schema to avoid InjectedState errors
    """
    from app.tools.agent_tools_fixed import (
        get_contact_details_with_task,
        escalate_to_supervisor,
        update_contact_with_context,
        save_important_context
    )
    
    try:
        # Check lead score boundaries
        lead_score = state.get("lead_score", 0)
        if lead_score > 4:
            logger.info(f"Score {lead_score} too high for Maria (handles 0-4)")
            return {
                "needs_rerouting": True,
                "escalation_reason": "wrong_agent",
                "escalation_details": f"Score {lead_score} too high for Maria"
            }
        
        # Create model and tools
        model = create_openai_model(temperature=0.7)
        tools = [
            get_contact_details_with_task,
            escalate_to_supervisor,
            update_contact_with_context,
            save_important_context
        ]
        
        # Dynamic prompt based on state
        def maria_prompt(state: MinimalState) -> str:
            extracted_data = state.get("extracted_data", {})
            return f"""You are Maria, a WhatsApp automation specialist for Main Outlet Media.

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

⚡ CRITICAL RULES:
- Lead score 0-4 only (5+ → escalate immediately)
- One strategic question at a time
- Always move toward booking a demo
- Speak conversational Mexican Spanish

Remember: You're not just collecting data - you're solving their WhatsApp communication problem!"""
        
        # Create agent with state_schema
        agent = create_react_agent(
            model=model,
            tools=tools,
            state_schema=MinimalState,  # This enables InjectedState!
            prompt=maria_prompt,
            name="maria"
        )
        
        # Ensure required fields
        if "remaining_steps" not in state:
            state["remaining_steps"] = 10
            
        # Invoke agent
        result = await agent.ainvoke(state)
        
        logger.info("Maria completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error in Maria: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "current_agent": "maria",
            "messages": state.get("messages", [])
        }