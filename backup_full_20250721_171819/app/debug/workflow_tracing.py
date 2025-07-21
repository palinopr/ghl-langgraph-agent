"""
Workflow Node Decorators for Automatic Tracing
Add tracing to any workflow node with a simple decorator
"""
from functools import wraps
from typing import Dict, Any, Callable
import time
import asyncio
from app.debug.trace_collector import trace_event, trace_error
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_tracing")


def trace_node(node_name: str):
    """
    Decorator to automatically trace workflow nodes
    
    Usage:
        @trace_node("receptionist")
        async def receptionist_node(state: Dict[str, Any]) -> Dict[str, Any]:
            # Your node logic here
            return state
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            # Get trace ID from state
            trace_id = state.get("_trace_id", "unknown")
            
            # Log node start
            start_time = time.time()
            trace_event(trace_id, f"{node_name}_start", {
                "node": node_name,
                "contact_id": state.get("contact_id", "unknown")
            })
            
            try:
                # Execute node
                if asyncio.iscoroutinefunction(func):
                    result = await func(state, *args, **kwargs)
                else:
                    result = func(state, *args, **kwargs)
                
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Extract key information based on node type
                node_data = _extract_node_data(node_name, state, result)
                
                # Log node completion
                trace_event(trace_id, f"{node_name}_complete", {
                    **node_data,
                    "duration_ms": duration_ms
                }, duration_ms)
                
                return result
                
            except Exception as e:
                # Log error
                trace_error(trace_id, f"{node_name}_node", e, {
                    "state_keys": list(state.keys()),
                    "contact_id": state.get("contact_id", "unknown")
                })
                raise
        
        return wrapper
    return decorator


def trace_tool(tool_name: str):
    """
    Decorator to trace tool executions
    
    Usage:
        @trace_tool("check_calendar")
        async def check_calendar_availability(...):
            # Tool logic
            return result
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Try to get trace ID from state parameter
            trace_id = "unknown"
            
            # Look for state in kwargs or args
            state = kwargs.get("state")
            if not state and args:
                # Check if any arg is a dict with _trace_id
                for arg in args:
                    if isinstance(arg, dict) and "_trace_id" in arg:
                        state = arg
                        break
            
            if state and isinstance(state, dict):
                trace_id = state.get("_trace_id", "unknown")
            
            # Log tool start
            start_time = time.time()
            tool_input = {
                "tool": tool_name,
                "args": str(args)[:200] if args else None,
                "kwargs": str(kwargs)[:200] if kwargs else None
            }
            
            trace_event(trace_id, "tool_start", tool_input)
            
            try:
                # Execute tool
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log tool completion
                trace_event(trace_id, "tool_complete", {
                    "tool": tool_name,
                    "success": True,
                    "result_type": type(result).__name__,
                    "duration_ms": duration_ms
                }, duration_ms)
                
                return result
                
            except Exception as e:
                # Log error
                trace_error(trace_id, f"{tool_name}_tool", e, tool_input)
                raise
        
        return wrapper
    return decorator


def _extract_node_data(node_name: str, state: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant data based on node type"""
    data = {"node": node_name}
    
    if node_name == "receptionist":
        data.update({
            "messages_loaded": len(state.get("conversation_history", [])),
            "contact_loaded": bool(state.get("contact_info")),
            "custom_fields_loaded": len(state.get("previous_custom_fields", {}))
        })
    
    elif node_name == "intelligence":
        data.update({
            "lead_score": result.get("lead_score", state.get("lead_score", 0)),
            "score_reasoning": result.get("score_reasoning", state.get("score_reasoning", "")),
            "suggested_agent": result.get("suggested_agent", state.get("suggested_agent", ""))
        })
    
    elif node_name == "supervisor":
        data.update({
            "current_agent": state.get("current_agent"),
            "next_agent": result.get("next_agent", state.get("next_agent")),
            "routing_attempts": state.get("routing_attempts", 0),
            "needs_rerouting": result.get("needs_rerouting", False)
        })
    
    elif node_name in ["maria", "carlos", "sofia"]:
        # Get the last message from the agent
        messages = result.get("messages", state.get("messages", []))
        last_ai_message = None
        for msg in reversed(messages):
            if hasattr(msg, "role") and msg.role == "assistant":
                last_ai_message = msg.content
                break
        
        data.update({
            "agent": node_name,
            "response_preview": last_ai_message[:100] if last_ai_message else None,
            "escalation": result.get("needs_rerouting", False)
        })
    
    elif node_name == "responder":
        data.update({
            "message_sent": result.get("message_sent", False),
            "message_length": len(state.get("last_sent_message", ""))
        })
    
    return data


# Function to inject tracing into existing workflow
def add_tracing_to_workflow(workflow_nodes: Dict[str, Callable]) -> Dict[str, Callable]:
    """
    Add tracing to all nodes in a workflow
    
    Usage:
        nodes = {
            "receptionist": receptionist_node,
            "intelligence": intelligence_node,
            ...
        }
        traced_nodes = add_tracing_to_workflow(nodes)
    """
    traced_nodes = {}
    
    for node_name, node_func in workflow_nodes.items():
        traced_nodes[node_name] = trace_node(node_name)(node_func)
    
    return traced_nodes


# Helper to trace specific events in workflow
def trace_workflow_event(state: Dict[str, Any], event_type: str, data: Dict[str, Any]):
    """Trace a custom event in the workflow"""
    trace_id = state.get("_trace_id", "unknown")
    trace_event(trace_id, event_type, data)


# Helper to trace routing decisions
def trace_routing(state: Dict[str, Any], from_node: str, to_node: str, reason: str = ""):
    """Trace routing decisions"""
    trace_id = state.get("_trace_id", "unknown")
    trace_event(trace_id, "routing_decision", {
        "from": from_node,
        "to": to_node,
        "reason": reason,
        "current_score": state.get("lead_score", 0),
        "routing_attempts": state.get("routing_attempts", 0)
    })


# Export all tracing functions
__all__ = [
    "trace_node",
    "trace_tool", 
    "add_tracing_to_workflow",
    "trace_workflow_event",
    "trace_routing"
]