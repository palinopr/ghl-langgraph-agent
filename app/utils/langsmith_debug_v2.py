"""
Enhanced LangSmith Debug Integration for LangGraph
Uses proper LangGraph-compatible logging approach
"""
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import json
from datetime import datetime
from langchain_core.messages import BaseMessage
import structlog
from app.utils.simple_logger import get_logger

logger = get_logger("langsmith_debug_v2")


class LangGraphDebugger:
    """LangGraph-compatible debugger that adds rich logging"""
    
    @staticmethod
    def create_debug_wrapper(node_name: str):
        """Create a debug wrapper that adds logging to node execution"""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                # Log entry with rich context
                entry_log = {
                    "event": f"{node_name}_entry",
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": state.get("thread_id"),
                    "contact_id": state.get("contact_id"),
                    "message_count": len(state.get("messages", [])),
                    "state_keys": list(state.keys()),
                    "current_agent": state.get("current_agent"),
                    "lead_score": state.get("lead_score"),
                }
                
                # Extract last message
                messages = state.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'content'):
                        entry_log["last_message"] = last_msg.content[:200]
                
                logger.info(f"🔍 {node_name} ENTRY", **entry_log)
                
                # Execute the node
                try:
                    result = await func(state)
                    
                    # Log exit with changes
                    exit_log = {
                        "event": f"{node_name}_exit",
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                        "changes": list(result.keys()) if result else [],
                    }
                    
                    # Log specific changes
                    if result:
                        if "messages" in result:
                            exit_log["messages_added"] = len(result["messages"])
                        if "next_agent" in result:
                            exit_log["routing_to"] = result["next_agent"]
                        if "lead_score" in result:
                            exit_log["new_lead_score"] = result["lead_score"]
                            exit_log["score_changed"] = result["lead_score"] != state.get("lead_score", 0)
                    
                    logger.info(f"✅ {node_name} EXIT", **exit_log)
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    error_log = {
                        "event": f"{node_name}_error",
                        "timestamp": datetime.now().isoformat(),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "success": False,
                    }
                    logger.error(f"❌ {node_name} ERROR", **error_log)
                    raise
            
            @wraps(func)
            def sync_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
                # Same logic but synchronous
                entry_log = {
                    "event": f"{node_name}_entry",
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": state.get("thread_id"),
                    "contact_id": state.get("contact_id"),
                    "message_count": len(state.get("messages", [])),
                    "state_keys": list(state.keys()),
                }
                
                logger.info(f"🔍 {node_name} ENTRY", **entry_log)
                
                try:
                    result = func(state)
                    
                    exit_log = {
                        "event": f"{node_name}_exit",
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                        "changes": list(result.keys()) if result else [],
                    }
                    
                    logger.info(f"✅ {node_name} EXIT", **exit_log)
                    
                    return result
                    
                except Exception as e:
                    error_log = {
                        "event": f"{node_name}_error",
                        "timestamp": datetime.now().isoformat(),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "success": False,
                    }
                    logger.error(f"❌ {node_name} ERROR", **error_log)
                    raise
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    def log_analysis_result(analysis: Dict[str, Any], context: str = ""):
        """Log analysis results with rich context"""
        log_data = {
            "event": f"analysis_{context}",
            "timestamp": datetime.now().isoformat(),
            "lead_score": analysis.get("lead_score"),
            "intent": analysis.get("intent"),
            "urgency": analysis.get("urgency"),
            "sentiment": analysis.get("sentiment"),
            "extracted_data": analysis.get("extracted_data", {}),
        }
        logger.info(f"📊 Analysis: {context}", **log_data)
    
    @staticmethod
    def log_routing_decision(from_agent: str, to_agent: str, reason: str, score: int):
        """Log routing decisions"""
        log_data = {
            "event": "routing_decision",
            "timestamp": datetime.now().isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason,
            "lead_score": score,
        }
        logger.info(f"🔀 Routing: {from_agent} → {to_agent}", **log_data)
    
    @staticmethod
    def log_tool_execution(tool_name: str, inputs: Dict[str, Any], output: Any, error: Optional[Exception] = None):
        """Log tool execution details"""
        log_data = {
            "event": f"tool_{tool_name}",
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "success": error is None,
        }
        
        # Add safe representations of inputs/outputs
        if inputs:
            log_data["input_keys"] = list(inputs.keys())
            log_data["input_preview"] = str(inputs)[:200]
        
        if output and not error:
            log_data["output_preview"] = str(output)[:200]
        
        if error:
            log_data["error_type"] = type(error).__name__
            log_data["error_message"] = str(error)
        
        if error:
            logger.error(f"🔧 Tool Error: {tool_name}", **log_data)
        else:
            logger.info(f"🔧 Tool Success: {tool_name}", **log_data)
    
    @staticmethod
    def log_api_call(service: str, endpoint: str, success: bool, details: Dict[str, Any] = None):
        """Log external API calls"""
        log_data = {
            "event": f"api_{service}",
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "endpoint": endpoint,
            "success": success,
        }
        
        if details:
            log_data.update(details)
        
        if success:
            logger.info(f"🌐 API Success: {service} - {endpoint}", **log_data)
        else:
            logger.error(f"🌐 API Error: {service} - {endpoint}", **log_data)


# Create singleton instance
debugger = LangGraphDebugger()


# Convenience functions
def debug_node(node_name: str):
    """Decorator to add comprehensive debugging to any node"""
    return debugger.create_debug_wrapper(node_name)


def log_analysis(analysis: Dict[str, Any], context: str = ""):
    """Log analysis results"""
    debugger.log_analysis_result(analysis, context)


def log_routing(from_agent: str, to_agent: str, reason: str, score: int):
    """Log routing decision"""
    debugger.log_routing_decision(from_agent, to_agent, reason, score)


def log_tool(tool_name: str, inputs: Dict[str, Any], output: Any, error: Optional[Exception] = None):
    """Log tool execution"""
    debugger.log_tool_execution(tool_name, inputs, output, error)


def log_api(service: str, endpoint: str, success: bool, **details):
    """Log API call"""
    debugger.log_api_call(service, endpoint, success, details)


# Export
__all__ = [
    "LangGraphDebugger",
    "debugger",
    "debug_node",
    "log_analysis",
    "log_routing",
    "log_tool",
    "log_api"
]