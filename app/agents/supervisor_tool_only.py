"""
Supervisor Agent - Tool-Only Implementation
This supervisor ONLY uses tools and NEVER responds with text
"""
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model
from app.state.message_manager import MessageManager

logger = get_logger("supervisor_tool_only")


@tool
def route_to_agent(agent_name: str, task_description: str) -> str:
    """
    Route conversation to the appropriate agent.
    
    Args:
        agent_name: One of 'maria', 'carlos', or 'sofia'
        task_description: Brief description of the task in Spanish
    """
    if agent_name not in ['maria', 'carlos', 'sofia']:
        raise ValueError(f"Invalid agent name: {agent_name}")
    return f"HANDOFF:{agent_name}:{task_description}"


async def supervisor_tool_only_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor that ONLY uses tools to route, NEVER responds with text.
    Uses direct LLM call with tool_choice="required" to guarantee tool usage.
    """
    try:
        lead_score = state.get("lead_score", 0)
        logger.info(f"Tool-only supervisor processing - Lead score: {lead_score}")
        
        # Determine which agent based on score
        if lead_score >= 8:
            target_agent = "sofia"
            task = "Cliente listo para agendar demo"
        elif lead_score >= 5:
            target_agent = "carlos"
            task = "Cliente necesita calificación"
        else:
            target_agent = "maria"
            task = "Atender al cliente"
        
        # Create model with forced tool usage
        model = create_openai_model(temperature=0.0)
        model_with_tools = model.bind_tools(
            [route_to_agent],
            tool_choice="required"  # FORCE tool usage
        )
        
        # Simple prompt that just states the routing decision
        prompt = f"""Route this conversation.
Lead Score: {lead_score}
Required Action: route_to_agent('{target_agent}', '{task}')"""
        
        # Get the tool call from the model
        response = await model_with_tools.ainvoke(prompt)
        
        # Extract tool calls
        if not response.tool_calls:
            # Fallback - create manual tool call
            logger.warning("No tool calls found, creating manual routing")
            tool_call = {
                "name": "route_to_agent",
                "args": {"agent_name": target_agent, "task_description": task},
                "id": "manual_routing"
            }
            response.tool_calls = [tool_call]
        
        # Execute the tool
        tool_node = ToolNode([route_to_agent])
        tool_result = await tool_node.ainvoke({"messages": [response]})
        
        # Extract the handoff message
        handoff_msg = None
        for msg in tool_result.get("messages", []):
            if isinstance(msg, ToolMessage) and msg.content.startswith("HANDOFF:"):
                handoff_msg = msg
                break
        
        if handoff_msg:
            parts = handoff_msg.content.split(":", 2)
            if len(parts) >= 3:
                _, agent, task = parts
                logger.info(f"✅ Tool-only routing to {agent}: {task}")
                
                # Return ONLY the routing information, no messages
                return {
                    "next_agent": agent,
                    "agent_task": task,
                    "supervisor_complete": True,
                    "routing_reason": f"Routed by score ({lead_score})"
                }
        
        # Fallback routing
        logger.warning("Tool execution failed, using fallback routing")
        return {
            "next_agent": target_agent,
            "agent_task": task,
            "supervisor_complete": True,
            "routing_reason": f"Fallback routing by score ({lead_score})"
        }
        
    except Exception as e:
        logger.error(f"Tool-only supervisor error: {str(e)}", exc_info=True)
        # Default to maria on error
        return {
            "next_agent": "maria",
            "agent_task": "Atender al cliente",
            "supervisor_complete": True,
            "routing_reason": f"Error routing: {str(e)}"
        }


# Export
__all__ = ["supervisor_tool_only_node", "route_to_agent"]