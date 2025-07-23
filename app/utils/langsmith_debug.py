"""
Comprehensive LangSmith Debug Integration
Captures EVERYTHING for maximum visibility in LangSmith traces
"""
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import json
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.callbacks import CallbackManagerForLLMRun
from langsmith import Client
try:
    from langsmith import traceable
except ImportError:
    # Fallback if traceable is not available
    def traceable(**kwargs):
        def decorator(func):
            return func
        return decorator
try:
    from langsmith.run_helpers import get_current_run_tree
except ImportError:
    def get_current_run_tree():
        return None
import structlog
from app.utils.simple_logger import get_logger

logger = get_logger("langsmith_debug")

# Initialize LangSmith client
langsmith_client = Client()


class LangSmithDebugger:
    """Comprehensive debugger that sends everything to LangSmith"""
    
    @staticmethod
    def _get_message_content(msg: Any) -> str:
        """Safely extract content from a message regardless of format"""
        if isinstance(msg, dict):
            return msg.get('content', str(msg))
        elif hasattr(msg, 'content'):
            return msg.content
        else:
            return str(msg)
    
    @staticmethod
    def log_metadata(metadata: Dict[str, Any], name: str = "debug_info"):
        """Add metadata to current LangSmith run"""
        try:
            run_tree = get_current_run_tree()
            if run_tree:
                # Use the correct API for adding metadata
                if hasattr(run_tree, 'add_metadata'):
                    run_tree.add_metadata({name: metadata})
                elif hasattr(run_tree, 'metadata'):
                    # Fallback: directly update metadata if available
                    if run_tree.metadata is None:
                        run_tree.metadata = {}
                    run_tree.metadata[name] = metadata
                else:
                    # If neither method is available, just log locally
                    logger.debug(f"LangSmith metadata ({name}): {metadata}")
        except Exception as e:
            logger.error(f"Failed to log metadata to LangSmith: {e}")
    
    @staticmethod
    def log_state_snapshot(state: Dict[str, Any], phase: str = "unknown"):
        """Log complete state snapshot to LangSmith"""
        try:
            # Extract key information
            messages = state.get("messages", [])
            
            snapshot = {
                "phase": phase,
                "timestamp": datetime.now().isoformat(),
                "thread_id": state.get("thread_id"),
                "contact_id": state.get("contact_id"),
                "current_agent": state.get("current_agent"),
                "next_agent": state.get("next_agent"),
                "lead_score": state.get("lead_score"),
                "message_count": len(messages),
                "last_message": LangSmithDebugger._get_message_content(messages[-1]) if messages else None,
                "state_keys": list(state.keys()),
                "extracted_data": state.get("extracted_data", {}),
                "routing_reason": state.get("routing_reason"),
                "needs_escalation": state.get("needs_escalation"),
                "agent_task": state.get("agent_task"),
            }
            
            # Add message breakdown
            message_types = {}
            for msg in messages:
                msg_type = type(msg).__name__
                message_types[msg_type] = message_types.get(msg_type, 0) + 1
            snapshot["message_types"] = message_types
            
            # Log to LangSmith
            LangSmithDebugger.log_metadata(snapshot, f"state_snapshot_{phase}")
            
        except Exception as e:
            logger.error(f"Failed to log state snapshot: {e}")
    
    @staticmethod
    def create_debug_wrapper(node_name: str, include_state_snapshots: bool = True):
        """Create a debug wrapper for any node that logs everything to LangSmith"""
        def decorator(func: Callable):
            @wraps(func)
            @traceable(
                name=f"{node_name}_debug",
                metadata={
                    "node_type": "agent" if "agent" in node_name else "system",
                    "debug_enabled": True
                }
            )
            async def async_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                # Log entry
                entry_metadata = {
                    "phase": "entry",
                    "node": node_name,
                    "timestamp": datetime.now().isoformat(),
                    "input_state_keys": list(state.keys()),
                    "thread_id": state.get("thread_id"),
                    "contact_id": state.get("contact_id"),
                }
                LangSmithDebugger.log_metadata(entry_metadata, f"{node_name}_entry")
                
                # Log state snapshot on entry
                if include_state_snapshots:
                    LangSmithDebugger.log_state_snapshot(state, f"{node_name}_entry")
                
                # Execute the node
                try:
                    result = await func(state)
                    
                    # Log exit
                    exit_metadata = {
                        "phase": "exit",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                        "output_keys": list(result.keys()) if result else [],
                        "success": True,
                    }
                    LangSmithDebugger.log_metadata(exit_metadata, f"{node_name}_exit")
                    
                    # Log state changes
                    if result:
                        changes = {
                            "messages_added": len(result.get("messages", [])),
                            "state_updates": {k: v for k, v in result.items() if k != "messages"},
                        }
                        LangSmithDebugger.log_metadata(changes, f"{node_name}_changes")
                    
                    # Log state snapshot on exit
                    if include_state_snapshots and result:
                        merged_state = {**state, **result}
                        LangSmithDebugger.log_state_snapshot(merged_state, f"{node_name}_exit")
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    error_metadata = {
                        "phase": "error",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "success": False,
                    }
                    LangSmithDebugger.log_metadata(error_metadata, f"{node_name}_error")
                    raise
            
            @wraps(func)
            @traceable(
                name=f"{node_name}_debug",
                metadata={
                    "node_type": "agent" if "agent" in node_name else "system",
                    "debug_enabled": True
                }
            )
            def sync_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                # Same logic but synchronous
                entry_metadata = {
                    "phase": "entry",
                    "node": node_name,
                    "timestamp": datetime.now().isoformat(),
                    "input_state_keys": list(state.keys()),
                    "thread_id": state.get("thread_id"),
                    "contact_id": state.get("contact_id"),
                }
                LangSmithDebugger.log_metadata(entry_metadata, f"{node_name}_entry")
                
                if include_state_snapshots:
                    LangSmithDebugger.log_state_snapshot(state, f"{node_name}_entry")
                
                try:
                    result = func(state)
                    
                    exit_metadata = {
                        "phase": "exit",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                        "output_keys": list(result.keys()) if result else [],
                        "success": True,
                    }
                    LangSmithDebugger.log_metadata(exit_metadata, f"{node_name}_exit")
                    
                    if result:
                        changes = {
                            "messages_added": len(result.get("messages", [])),
                            "state_updates": {k: v for k, v in result.items() if k != "messages"},
                        }
                        LangSmithDebugger.log_metadata(changes, f"{node_name}_changes")
                    
                    if include_state_snapshots and result:
                        merged_state = {**state, **result}
                        LangSmithDebugger.log_state_snapshot(merged_state, f"{node_name}_exit")
                    
                    return result
                    
                except Exception as e:
                    error_metadata = {
                        "phase": "error",
                        "node": node_name,
                        "timestamp": datetime.now().isoformat(),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "success": False,
                    }
                    LangSmithDebugger.log_metadata(error_metadata, f"{node_name}_error")
                    raise
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    def log_tool_execution(tool_name: str, inputs: Dict[str, Any], output: Any, error: Optional[Exception] = None):
        """Log tool execution details to LangSmith"""
        tool_metadata = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "inputs": inputs,
            "output": str(output)[:1000] if output else None,  # Truncate large outputs
            "success": error is None,
            "error": str(error) if error else None,
        }
        LangSmithDebugger.log_metadata(tool_metadata, f"tool_{tool_name}")
    
    @staticmethod
    def log_routing_decision(from_agent: str, to_agent: str, reason: str, score: int):
        """Log routing decisions to LangSmith"""
        routing_metadata = {
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
            "lead_score": score,
            "timestamp": datetime.now().isoformat(),
        }
        LangSmithDebugger.log_metadata(routing_metadata, "routing_decision")
    
    @staticmethod
    def log_message_flow(messages: List[BaseMessage], phase: str = "unknown"):
        """Log message flow analysis to LangSmith"""
        message_analysis = {
            "phase": phase,
            "total_messages": len(messages),
            "message_types": {},
            "last_5_messages": [],
        }
        
        # Count message types
        for msg in messages:
            msg_type = type(msg).__name__
            message_analysis["message_types"][msg_type] = message_analysis["message_types"].get(msg_type, 0) + 1
        
        # Get last 5 messages
        for msg in messages[-5:]:
            msg_info = {
                "type": type(msg).__name__,
                "content": msg.content[:200] if hasattr(msg, 'content') else str(msg)[:200],
                "has_tool_calls": hasattr(msg, 'tool_calls') and bool(msg.tool_calls),
                "name": getattr(msg, 'name', None),
            }
            message_analysis["last_5_messages"].append(msg_info)
        
        LangSmithDebugger.log_metadata(message_analysis, f"message_flow_{phase}")
    
    @staticmethod
    def create_traceable_tool(tool_func: Callable, tool_name: str):
        """Create a traceable version of a tool that logs to LangSmith"""
        @wraps(tool_func)
        @traceable(
            name=f"tool_{tool_name}",
            metadata={"tool_type": "ghl_integration", "debug_enabled": True}
        )
        def wrapper(*args, **kwargs):
            # Log inputs
            LangSmithDebugger.log_metadata({
                "args": str(args)[:500],
                "kwargs": str(kwargs)[:500],
            }, f"tool_{tool_name}_inputs")
            
            try:
                result = tool_func(*args, **kwargs)
                # Log success
                LangSmithDebugger.log_tool_execution(
                    tool_name, 
                    {"args": args, "kwargs": kwargs}, 
                    result
                )
                return result
            except Exception as e:
                # Log error
                LangSmithDebugger.log_tool_execution(
                    tool_name, 
                    {"args": args, "kwargs": kwargs}, 
                    None, 
                    e
                )
                raise
        
        return wrapper


# Create singleton instance
debugger = LangSmithDebugger()


# Convenience functions
def debug_node(node_name: str):
    """Decorator to add comprehensive debugging to any node"""
    return debugger.create_debug_wrapper(node_name)


def log_to_langsmith(metadata: Dict[str, Any], name: str = "custom_debug"):
    """Quick function to log any metadata to LangSmith"""
    debugger.log_metadata(metadata, name)


def debug_state(state: Dict[str, Any], context: str = ""):
    """Quick function to debug state at any point"""
    debugger.log_state_snapshot(state, context)


# Export
__all__ = [
    "LangSmithDebugger",
    "debugger",
    "debug_node",
    "log_to_langsmith",
    "debug_state"
]