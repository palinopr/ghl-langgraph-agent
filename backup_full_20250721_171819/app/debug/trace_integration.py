"""
Simple integration to add tracing to workflow execution
"""
from typing import Dict, Any
from app.debug.trace_collector import trace_event, trace_error
from app.debug.workflow_tracing import trace_node
from app.utils.simple_logger import get_logger

logger = get_logger("trace_integration")


# Create wrapped versions of nodes with tracing
def create_traced_receptionist(original_node):
    """Wrap receptionist node with tracing"""
    @trace_node("receptionist")
    async def traced_receptionist(state: Dict[str, Any]) -> Dict[str, Any]:
        # Add specific traces for receptionist
        trace_id = state.get("_trace_id", "unknown")
        
        # Trace data loading
        trace_event(trace_id, "state_loading", {
            "contact_id": state.get("contact_id"),
            "has_previous_data": bool(state.get("previous_custom_fields"))
        })
        
        # Call original node
        result = await original_node(state)
        
        # Trace what was loaded
        trace_event(trace_id, "state_loaded", {
            "messages_count": len(state.get("conversation_history", [])),
            "previous_score": state.get("previous_custom_fields", {}).get("score", 0),
            "contact_name": state.get("contact_info", {}).get("firstName", "Unknown")
        })
        
        return result
    
    return traced_receptionist


def create_traced_intelligence(original_node):
    """Wrap intelligence node with tracing"""
    @trace_node("intelligence")
    async def traced_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = state.get("_trace_id", "unknown")
        
        # Call original node
        result = await original_node(state)
        
        # Trace analysis results
        trace_event(trace_id, "intelligence_analysis", {
            "lead_score": result.get("lead_score", state.get("lead_score", 0)),
            "score_reasoning": result.get("score_reasoning", state.get("score_reasoning", "")),
            "suggested_agent": result.get("suggested_agent", state.get("suggested_agent", "")),
            "extracted_data": result.get("extracted_data", state.get("extracted_data", {}))
        })
        
        return result
    
    return traced_intelligence


def create_traced_supervisor(original_node):
    """Wrap supervisor node with tracing"""
    @trace_node("supervisor")
    async def traced_supervisor(state: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = state.get("_trace_id", "unknown")
        
        # Trace before routing
        trace_event(trace_id, "routing_decision_start", {
            "current_score": state.get("lead_score", 0),
            "current_agent": state.get("current_agent"),
            "routing_attempts": state.get("routing_attempts", 0)
        })
        
        # Call original node
        result = await original_node(state)
        
        # Trace routing result
        trace_event(trace_id, "agent_routing", {
            "from": "supervisor",
            "to": result.get("next_agent", state.get("next_agent", "unknown")),
            "routing_reason": result.get("escalation_reason", "score-based routing"),
            "needs_rerouting": result.get("needs_rerouting", False)
        })
        
        return result
    
    return traced_supervisor


def create_traced_agent(agent_name: str, original_node):
    """Wrap agent node with tracing"""
    @trace_node(agent_name)
    async def traced_agent(state: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = state.get("_trace_id", "unknown")
        
        # Trace agent start
        trace_event(trace_id, f"{agent_name}_processing", {
            "agent": agent_name,
            "context": state.get("agent_context", {})
        })
        
        # Call original node
        result = await original_node(state)
        
        # Extract response
        messages = result.get("messages", state.get("messages", []))
        last_ai_message = ""
        for msg in reversed(messages):
            if hasattr(msg, "role") and msg.role == "assistant":
                last_ai_message = msg.content
                break
        
        # Trace agent response
        trace_event(trace_id, "agent_response", {
            "agent": agent_name,
            "response_preview": last_ai_message[:200] if last_ai_message else "",
            "needs_rerouting": result.get("needs_rerouting", False),
            "escalation": result.get("escalation_reason", "")
        })
        
        return result
    
    return traced_agent


def create_traced_responder(original_node):
    """Wrap responder node with tracing"""
    @trace_node("responder")
    async def traced_responder(state: Dict[str, Any]) -> Dict[str, Any]:
        trace_id = state.get("_trace_id", "unknown")
        
        # Get message to send
        messages = state.get("messages", [])
        message_to_send = ""
        for msg in reversed(messages):
            if hasattr(msg, "role") and msg.role == "assistant":
                message_to_send = msg.content
                break
        
        # Trace before sending
        trace_event(trace_id, "sending_message", {
            "message_length": len(message_to_send),
            "has_timing_delay": True
        })
        
        # Call original node
        result = await original_node(state)
        
        # Trace completion
        trace_event(trace_id, "message_sent", {
            "message": message_to_send[:200],
            "sent": result.get("message_sent", False)
        })
        
        return result
    
    return traced_responder


# Main function to add tracing to workflow
def add_workflow_tracing(workflow_nodes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add comprehensive tracing to all workflow nodes
    
    Usage:
        # In your workflow file
        from app.debug.trace_integration import add_workflow_tracing
        
        # After creating nodes
        nodes = {
            "receptionist": receptionist_node,
            "intelligence": intelligence_node,
            ...
        }
        
        # Add tracing
        traced_nodes = add_workflow_tracing(nodes)
        
        # Use traced nodes in workflow
        for name, node in traced_nodes.items():
            workflow.add_node(name, node)
    """
    traced_nodes = {}
    
    # Map node names to specific tracing functions
    node_tracers = {
        "receptionist": create_traced_receptionist,
        "intelligence": create_traced_intelligence,
        "supervisor": create_traced_supervisor,
        "supervisor_ai": create_traced_supervisor,
        "responder": create_traced_responder,
        "responder_streaming": create_traced_responder
    }
    
    # Agent nodes
    agent_names = ["maria", "carlos", "sofia"]
    
    for node_name, node_func in workflow_nodes.items():
        if node_name in node_tracers:
            # Use specific tracer
            traced_nodes[node_name] = node_tracers[node_name](node_func)
        elif node_name in agent_names:
            # Use agent tracer
            traced_nodes[node_name] = create_traced_agent(node_name, node_func)
        else:
            # Use generic tracer
            traced_nodes[node_name] = trace_node(node_name)(node_func)
    
    logger.info(f"Added tracing to {len(traced_nodes)} workflow nodes")
    return traced_nodes


# Export
__all__ = ["add_workflow_tracing"]