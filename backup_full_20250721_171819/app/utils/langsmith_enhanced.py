"""
Enhanced LangSmith Tracing for Real-World Debugging
Makes it easy to track what's happening in production
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from functools import wraps
import traceback
from langsmith import Client
from langchain_core.tracers.context import tracing_v2_enabled
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.utils.simple_logger import get_logger

logger = get_logger("langsmith_enhanced")


class WorkflowTracer:
    """Enhanced tracer for debugging GHL workflows"""
    
    def __init__(self, contact_id: str, webhook_data: Dict[str, Any]):
        self.contact_id = contact_id
        self.webhook_data = webhook_data
        self.workflow_id = f"{contact_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.events = []
        self.client = None
        
        try:
            self.client = Client()
        except:
            logger.warning("LangSmith client not available")
    
    def trace_webhook_received(self):
        """Log when webhook is received"""
        self._add_event("webhook_received", {
            "message": self.webhook_data.get("message", ""),
            "type": self.webhook_data.get("type", "WhatsApp"),
            "direction": self.webhook_data.get("direction", "inbound"),
            "contact_id": self.contact_id
        })
    
    def trace_state_loading(self, state_data: Dict[str, Any]):
        """Log when state is loaded from GHL"""
        self._add_event("state_loaded", {
            "contact_name": state_data.get("contact_info", {}).get("firstName", "Unknown"),
            "previous_score": state_data.get("previous_custom_fields", {}).get("score", 0),
            "messages_loaded": len(state_data.get("conversation_history", [])),
            "custom_fields": list(state_data.get("previous_custom_fields", {}).keys())
        })
    
    def trace_intelligence_analysis(self, analysis_result: Dict[str, Any]):
        """Log intelligence layer analysis"""
        self._add_event("intelligence_analysis", {
            "lead_score": analysis_result.get("lead_score", 0),
            "score_reasoning": analysis_result.get("score_reasoning", ""),
            "extracted_data": analysis_result.get("extracted_data", {}),
            "suggested_agent": analysis_result.get("suggested_agent", "")
        })
    
    def trace_agent_routing(self, from_node: str, to_agent: str, context: Dict[str, Any]):
        """Log agent routing decisions"""
        self._add_event("agent_routing", {
            "from": from_node,
            "to": to_agent,
            "routing_reason": context.get("routing_reason", ""),
            "agent_context": context.get("agent_context", {}),
            "routing_attempt": context.get("routing_attempts", 0)
        })
    
    def trace_agent_response(self, agent_name: str, response: str, tools_used: List[str] = None):
        """Log agent responses"""
        self._add_event("agent_response", {
            "agent": agent_name,
            "response_preview": response[:200] + "..." if len(response) > 200 else response,
            "response_length": len(response),
            "tools_used": tools_used or [],
            "has_escalation": "escalate" in response.lower()
        })
    
    def trace_tool_execution(self, tool_name: str, tool_input: Dict[str, Any], tool_output: Any):
        """Log tool executions"""
        self._add_event("tool_execution", {
            "tool": tool_name,
            "input": self._safe_serialize(tool_input),
            "output_preview": str(tool_output)[:200],
            "success": tool_output is not None
        })
    
    def trace_ghl_update(self, update_type: str, data: Dict[str, Any]):
        """Log updates sent to GHL"""
        self._add_event("ghl_update", {
            "type": update_type,
            "data": self._safe_serialize(data),
            "fields_updated": list(data.keys()) if isinstance(data, dict) else []
        })
    
    def trace_message_sent(self, message: str, timing_delay: Optional[float] = None):
        """Log when message is sent to customer"""
        self._add_event("message_sent", {
            "message_preview": message[:100] + "..." if len(message) > 100 else message,
            "message_length": len(message),
            "timing_delay": timing_delay,
            "timestamp": datetime.now().isoformat()
        })
    
    def trace_error(self, error_location: str, error: Exception):
        """Log errors with full context"""
        self._add_event("error", {
            "location": error_location,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "workflow_state": self._get_current_state()
        })
    
    def trace_workflow_complete(self, final_state: Dict[str, Any]):
        """Log workflow completion"""
        self._add_event("workflow_complete", {
            "total_duration_ms": self._calculate_duration(),
            "final_score": final_state.get("lead_score", 0),
            "agent_path": self._get_agent_path(),
            "message_sent": final_state.get("message_sent", False),
            "total_events": len(self.events)
        })
    
    def get_trace_url(self) -> Optional[str]:
        """Get LangSmith trace URL for this workflow"""
        if self.client:
            project = os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent")
            return f"https://smith.langchain.com/{project}/runs?workflow_id={self.workflow_id}"
        return None
    
    def _add_event(self, event_type: str, data: Dict[str, Any]):
        """Add event to trace"""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "workflow_id": self.workflow_id,
            "contact_id": self.contact_id,
            "data": data
        }
        self.events.append(event)
        
        # Log to LangSmith as custom event
        if self.client:
            try:
                with tracing_v2_enabled(
                    project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
                    metadata={
                        "workflow_id": self.workflow_id,
                        "event_type": event_type,
                        "contact_id": self.contact_id
                    },
                    tags=["ghl-workflow", event_type]
                ):
                    logger.info(f"[{event_type}] {json.dumps(data, indent=2)}")
            except:
                pass
    
    def _safe_serialize(self, obj: Any) -> Any:
        """Safely serialize objects for logging"""
        try:
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            elif isinstance(obj, (list, tuple)):
                return [self._safe_serialize(item) for item in obj[:10]]  # Limit arrays
            elif isinstance(obj, dict):
                return {k: self._safe_serialize(v) for k, v in list(obj.items())[:20]}  # Limit dict size
            elif isinstance(obj, BaseMessage):
                return {"type": obj.__class__.__name__, "content": obj.content[:200]}
            else:
                return str(obj)[:200]
        except:
            return "<serialization_error>"
    
    def _calculate_duration(self) -> int:
        """Calculate workflow duration in milliseconds"""
        if len(self.events) >= 2:
            start = datetime.fromisoformat(self.events[0]["timestamp"])
            end = datetime.fromisoformat(self.events[-1]["timestamp"])
            return int((end - start).total_seconds() * 1000)
        return 0
    
    def _get_agent_path(self) -> List[str]:
        """Get the path of agents visited"""
        path = []
        for event in self.events:
            if event["type"] == "agent_routing":
                path.append(event["data"]["to"])
        return path
    
    def _get_current_state(self) -> Dict[str, Any]:
        """Get current workflow state for error context"""
        state = {
            "events_count": len(self.events),
            "last_agent": None,
            "last_score": None
        }
        
        for event in reversed(self.events):
            if event["type"] == "agent_routing" and not state["last_agent"]:
                state["last_agent"] = event["data"]["to"]
            elif event["type"] == "intelligence_analysis" and state["last_score"] is None:
                state["last_score"] = event["data"]["lead_score"]
        
        return state


# Decorator for tracing functions
def trace_workflow_step(step_name: str):
    """Decorator to trace workflow steps"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract tracer from state if available
            tracer = None
            if args and isinstance(args[0], dict) and "workflow_tracer" in args[0]:
                tracer = args[0]["workflow_tracer"]
            
            if tracer:
                tracer._add_event(f"{step_name}_start", {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
            
            try:
                result = await func(*args, **kwargs)
                
                if tracer:
                    tracer._add_event(f"{step_name}_complete", {
                        "function": func.__name__,
                        "success": True,
                        "result_type": type(result).__name__
                    })
                
                return result
                
            except Exception as e:
                if tracer:
                    tracer.trace_error(f"{step_name}:{func.__name__}", e)
                raise
        
        return wrapper
    return decorator


# Helper function to create tracer
def create_workflow_tracer(webhook_data: Dict[str, Any]) -> WorkflowTracer:
    """Create a new workflow tracer"""
    contact_id = webhook_data.get("contactId", "unknown")
    return WorkflowTracer(contact_id, webhook_data)


# Example usage in workflow
async def traced_workflow_example(webhook_data: Dict[str, Any]):
    """Example of how to use the tracer in your workflow"""
    tracer = create_workflow_tracer(webhook_data)
    
    # Add tracer to state
    state = {
        "workflow_tracer": tracer,
        "contact_id": webhook_data.get("contactId"),
        # ... other state fields
    }
    
    # Trace webhook received
    tracer.trace_webhook_received()
    
    # Your workflow continues...
    # Each node can access the tracer from state
    
    return state


# Export key functions
__all__ = [
    "WorkflowTracer",
    "create_workflow_tracer", 
    "trace_workflow_step"
]