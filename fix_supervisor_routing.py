#!/usr/bin/env python3
"""
Fix script to ensure supervisor ALWAYS routes and NEVER responds directly
This will replace the current supervisor.py with a fixed version
"""
import shutil
from pathlib import Path

def create_fixed_supervisor():
    """Create the fixed supervisor code"""
    return '''"""
Fixed Supervisor - ALWAYS routes, NEVER responds directly
Ensures proper handoff to agents based on lead scores
"""
from typing import Dict, Any, List, Optional, Literal
from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.state.minimal_state import MinimalState
from langchain_core.tools import tool
from typing_extensions import Annotated

logger = get_logger("supervisor")


# Handoff tools that return routing information
@tool
def handoff_to_sofia(
    task_description: Annotated[str, "Task for Sofia to complete in Spanish"]
) -> str:
    """
    Route to Sofia - Appointment Setting Specialist.
    ONLY use when:
    - Lead score is 8-10 (hot leads)
    - Customer is ready to book appointment
    - Has name, email, and $300+ budget confirmed
    """
    return f"HANDOFF:sofia:{task_description}"


@tool
def handoff_to_carlos(
    task_description: Annotated[str, "Task for Carlos to complete in Spanish"]
) -> str:
    """
    Route to Carlos - Lead Qualification Specialist.
    Use when:
    - Lead score is 5-7 (warm leads)
    - Customer needs qualification
    - Missing budget confirmation or details
    """
    return f"HANDOFF:carlos:{task_description}"


@tool
def handoff_to_maria(
    task_description: Annotated[str, "Task for Maria to complete in Spanish"]
) -> str:
    """
    Route to Maria - Customer Support Representative.
    Use when:
    - Lead score is 0-4 (cold leads) 
    - Score is 0 or unknown
    - Customer has general questions
    - New conversations just starting
    """
    return f"HANDOFF:maria:{task_description}"


def create_supervisor_with_tools():
    """Create supervisor that ONLY routes using tools"""
    model = create_openai_model(temperature=0.0)
    
    tools = [handoff_to_maria, handoff_to_carlos, handoff_to_sofia]
    
    # CRITICAL: Prompt that forces tool usage ONLY
    system_prompt = """You are a routing-only supervisor. You CANNOT talk to customers directly.

YOUR ONLY TASK: Analyze the lead score and use the appropriate handoff tool.

CRITICAL RULES:
1. You MUST use ONE of the handoff tools - NEVER respond to the customer
2. You CANNOT send any message to the customer
3. You CANNOT greet, analyze, or chat - ONLY route using tools
4. Even for "hola" or any greeting - use handoff_to_maria

ROUTING BASED ON SCORE:
- Score 0-4 or unknown → Use handoff_to_maria 
- Score 5-7 → Use handoff_to_carlos
- Score 8-10 → Use handoff_to_sofia

Current Lead Score: {lead_score}

IMPORTANT: Immediately use the handoff tool. The task description should be in Spanish.
Example: For "hola" with score 0, use: handoff_to_maria("Responder al saludo del cliente")

DO NOT RESPOND TO THE CUSTOMER - ONLY USE TOOLS!"""
    
    def build_prompt(state: MinimalState) -> List[AnyMessage]:
        lead_score = state.get("lead_score", 0)
        messages = state.get("messages", [])
        
        # Format the system prompt with current score
        formatted_system = system_prompt.format(lead_score=lead_score)
        
        return [{"role": "system", "content": formatted_system}] + messages
    
    # Create agent with state schema
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_schema=MinimalState,
        prompt=build_prompt,
        name="supervisor"
    )
    
    return agent


async def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Supervisor node that GUARANTEES routing"""
    try:
        # Ensure required fields
        for field, default in [("messages", []), ("thread_id", state.get("contact_id", "unknown")), ("remaining_steps", 10)]:
            if field not in state:
                state[field] = default
        
        lead_score = state.get("lead_score", 0)
        logger.info(f"Supervisor processing - Lead score: {lead_score}")
        
        # Create and run supervisor
        supervisor = create_supervisor_with_tools()
        result = await supervisor.ainvoke(state)
        
        # Extract routing from result
        routing_update = {
            "supervisor_complete": True,
            "messages": result.get("messages", [])
        }
        
        # Find handoff in messages
        handoff_found = False
        
        for msg in result.get("messages", []):
            # Check if AI message has tool calls
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    logger.info(f"✅ Supervisor used {len(msg.tool_calls)} tool(s)")
                    handoff_found = True
                elif msg.content and not msg.tool_calls:
                    # CRITICAL ERROR - supervisor responded directly!
                    logger.error(f"❌ CRITICAL: Supervisor responded directly: {msg.content[:100]}")
                    # Remove this message from output
                    routing_update["messages"] = [m for m in routing_update["messages"] if m != msg]
            
            # Check for handoff pattern
            if hasattr(msg, 'content') and isinstance(msg.content, str) and msg.content.startswith("HANDOFF:"):
                parts = msg.content.split(":", 2)
                if len(parts) >= 3:
                    _, agent, task = parts
                    routing_update.update({
                        "next_agent": agent,
                        "agent_task": task,
                        "routing_reason": f"Routed to {agent} by supervisor"
                    })
                    handoff_found = True
                    logger.info(f"✅ Routing to {agent}: {task}")
        
        # FAILSAFE: Force routing if no handoff detected
        if not handoff_found:
            logger.warning("⚠️ No handoff detected - forcing route based on score")
            
            # Determine agent based on score
            if lead_score >= 8:
                agent = "sofia"
            elif lead_score >= 5:
                agent = "carlos"
            else:
                agent = "maria"
            
            routing_update.update({
                "next_agent": agent,
                "agent_task": "Atender al cliente",
                "routing_reason": f"Forced routing to {agent} (score: {lead_score})"
            })
        
        return routing_update
        
    except Exception as e:
        logger.error(f"Supervisor error: {str(e)}", exc_info=True)
        return {
            "next_agent": "maria",
            "agent_task": "Atender al cliente",
            "supervisor_complete": True,
            "routing_reason": f"Error in supervisor: {str(e)}",
            "messages": state.get("messages", [])
        }


# Export
supervisor_official_node = supervisor_node
__all__ = ["supervisor_node", "supervisor_official_node", "create_supervisor_with_tools"]
'''


def fix_intelligence_scoring():
    """Create a simple intelligence fix for basic scoring"""
    return '''
# Add this to intelligence_node to ensure basic scoring happens

# For simple greetings, assign a base score
current_message = ""
for msg in reversed(state.get("messages", [])):
    if hasattr(msg, "content"):
        current_message = msg.content.lower()
        break

# Basic scoring for common messages
if not state.get("lead_score") or state.get("lead_score") == 0:
    if any(greeting in current_message for greeting in ["hola", "buenos días", "buenas tardes", "buenas noches", "saludos"]):
        # Simple greeting = score 1-2
        state["lead_score"] = 1
        state["lead_category"] = "cold"
        state["score_reasoning"] = "Simple greeting - needs initial engagement"
        logger.info("Applied basic scoring for greeting")
'''


def main():
    """Apply the fixes"""
    print("🔧 Fixing Supervisor Routing Issues")
    print("=" * 60)
    
    # Backup current supervisor
    supervisor_path = Path("app/agents/supervisor.py")
    backup_path = Path("app/agents/supervisor_backup_before_fix.py")
    
    if supervisor_path.exists():
        shutil.copy(supervisor_path, backup_path)
        print(f"✅ Backed up current supervisor to: {backup_path}")
    
    # Write fixed supervisor
    fixed_content = create_fixed_supervisor()
    supervisor_path.write_text(fixed_content)
    print(f"✅ Wrote fixed supervisor to: {supervisor_path}")
    
    # Show what needs to be done for intelligence
    print("\n📋 Intelligence Node Fix:")
    print("Add basic scoring for greetings in intelligence_node")
    print("This ensures lead_score > 0 for basic messages")
    
    print("\n🎯 What This Fixes:")
    print("1. ✅ Supervisor will NEVER respond directly")
    print("2. ✅ Always uses handoff tools for routing")
    print("3. ✅ Forces routing even if tools fail")
    print("4. ✅ Removes any direct AI responses")
    print("5. ✅ Routes to Maria for score 0-4 (including greetings)")
    
    print("\n📌 Next Steps:")
    print("1. Commit these changes")
    print("2. Deploy to fix the routing issue")
    print("3. Test with 'hola' - should route to Maria")


if __name__ == "__main__":
    main()