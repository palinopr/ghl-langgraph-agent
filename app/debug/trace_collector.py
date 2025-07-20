"""
In-Process Trace Collector for Real-Time Debugging
Captures everything that happens in your workflow for easy debugging
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Deque
from collections import deque
import traceback
from threading import Lock
import asyncio
from app.utils.simple_logger import get_logger

logger = get_logger("trace_collector")


class TraceCollector:
    """Collects traces from workflow execution for debugging"""
    
    def __init__(self, max_traces: int = 100):
        self.traces: Deque[Dict[str, Any]] = deque(maxlen=max_traces)
        self.active_traces: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        self.error_traces: Deque[Dict[str, Any]] = deque(maxlen=20)
        
    def start_trace(self, contact_id: str, webhook_data: Dict[str, Any]) -> str:
        """Start a new trace for a conversation"""
        trace_id = f"{contact_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        trace = {
            "trace_id": trace_id,
            "contact_id": contact_id,
            "started_at": datetime.now().isoformat(),
            "webhook_data": {
                "message": webhook_data.get("body", ""),
                "type": webhook_data.get("type", "WhatsApp"),
                "direction": webhook_data.get("direction", "inbound")
            },
            "events": [],
            "errors": [],
            "summary": {},
            "duration_ms": None,
            "status": "active"
        }
        
        with self.lock:
            self.active_traces[trace_id] = trace
            
        logger.info(f"Started trace: {trace_id}")
        return trace_id
    
    def add_event(self, trace_id: str, event_type: str, data: Dict[str, Any], duration_ms: Optional[int] = None):
        """Add an event to an active trace"""
        with self.lock:
            if trace_id not in self.active_traces:
                logger.warning(f"Trace {trace_id} not found")
                return
            
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "data": self._sanitize_data(data),
                "duration_ms": duration_ms
            }
            
            self.active_traces[trace_id]["events"].append(event)
            
            # Update summary based on event type
            self._update_summary(self.active_traces[trace_id], event_type, data)
    
    def add_error(self, trace_id: str, error_location: str, error: Exception, context: Dict[str, Any] = None):
        """Add an error to the trace"""
        with self.lock:
            if trace_id not in self.active_traces:
                return
            
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "location": error_location,
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
                "context": self._sanitize_data(context or {})
            }
            
            self.active_traces[trace_id]["errors"].append(error_data)
            self.active_traces[trace_id]["status"] = "error"
    
    def end_trace(self, trace_id: str, final_state: Dict[str, Any] = None):
        """Complete a trace and move to storage"""
        with self.lock:
            if trace_id not in self.active_traces:
                return
            
            trace = self.active_traces[trace_id]
            
            # Calculate duration
            start_time = datetime.fromisoformat(trace["started_at"])
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            trace["duration_ms"] = duration_ms
            
            # Set final status
            if trace["status"] == "active":
                trace["status"] = "completed"
            
            # Add final state if provided
            if final_state:
                trace["final_state"] = self._sanitize_data(final_state)
            
            # Store trace
            self.traces.append(trace)
            
            # If it has errors, also store in error traces
            if trace["errors"]:
                self.error_traces.append(trace)
            
            # Remove from active
            del self.active_traces[trace_id]
            
            logger.info(f"Completed trace: {trace_id} in {duration_ms}ms")
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific trace by ID"""
        with self.lock:
            # Check active traces first
            if trace_id in self.active_traces:
                return self.active_traces[trace_id].copy()
            
            # Check completed traces
            for trace in self.traces:
                if trace["trace_id"] == trace_id:
                    return trace.copy()
                    
        return None
    
    def get_last_trace(self) -> Optional[Dict[str, Any]]:
        """Get the most recent trace"""
        with self.lock:
            if self.traces:
                return self.traces[-1].copy()
        return None
    
    def get_last_error_trace(self) -> Optional[Dict[str, Any]]:
        """Get the most recent trace with errors"""
        with self.lock:
            if self.error_traces:
                return self.error_traces[-1].copy()
        return None
    
    def get_traces_for_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent traces for a specific contact"""
        with self.lock:
            contact_traces = []
            for trace in reversed(self.traces):
                if trace["contact_id"] == contact_id:
                    contact_traces.append(trace.copy())
                    if len(contact_traces) >= limit:
                        break
            return contact_traces
    
    def get_active_traces(self) -> List[Dict[str, Any]]:
        """Get all currently active traces"""
        with self.lock:
            return [trace.copy() for trace in self.active_traces.values()]
    
    def export_trace_for_debugging(self, trace_id: str) -> str:
        """Export a trace in a format easy to share for debugging"""
        trace = self.get_trace(trace_id)
        if not trace:
            return json.dumps({"error": "Trace not found"}, indent=2)
        
        # Create a simplified version for sharing
        debug_export = {
            "trace_id": trace["trace_id"],
            "contact_id": trace["contact_id"],
            "duration_ms": trace.get("duration_ms", "still running"),
            "status": trace["status"],
            "webhook_message": trace["webhook_data"]["message"],
            
            # Create a timeline of key events
            "timeline": self._create_timeline(trace),
            
            # Include errors if any
            "errors": trace["errors"],
            
            # Include summary
            "summary": trace["summary"],
            
            # Add debugging hints
            "debug_hints": self._generate_debug_hints(trace)
        }
        
        return json.dumps(debug_export, indent=2, ensure_ascii=False)
    
    def _sanitize_data(self, data: Any) -> Any:
        """Remove sensitive data and limit size"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip large fields
                if key in ["conversation_history", "messages"] and isinstance(value, list) and len(value) > 5:
                    sanitized[key] = f"<{len(value)} items>"
                # Limit string length
                elif isinstance(value, str) and len(value) > 500:
                    sanitized[key] = value[:500] + "..."
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data[:10]]  # Limit lists
        else:
            return data
    
    def _update_summary(self, trace: Dict[str, Any], event_type: str, data: Dict[str, Any]):
        """Update trace summary based on events"""
        summary = trace["summary"]
        
        # Track key milestones
        if event_type == "state_loaded":
            summary["messages_loaded"] = data.get("messages_count", 0)
            summary["previous_score"] = data.get("previous_score", 0)
            
        elif event_type == "intelligence_analysis":
            summary["lead_score"] = data.get("lead_score", 0)
            summary["suggested_agent"] = data.get("suggested_agent", "")
            
        elif event_type == "agent_routing":
            if "routing_path" not in summary:
                summary["routing_path"] = []
            summary["routing_path"].append(f"{data.get('from', '?')} → {data.get('to', '?')}")
            
        elif event_type == "message_sent":
            summary["message_sent"] = True
            summary["response_preview"] = data.get("message", "")[:100]
    
    def _create_timeline(self, trace: Dict[str, Any]) -> List[str]:
        """Create a human-readable timeline of events"""
        timeline = []
        
        for event in trace["events"]:
            timestamp = event["timestamp"].split("T")[1].split(".")[0]  # Just time
            event_type = event["type"]
            data = event["data"]
            
            # Format based on event type
            if event_type == "webhook_received":
                timeline.append(f"[{timestamp}] 📥 Received: '{data.get('message', '')}'")
                
            elif event_type == "intelligence_analysis":
                timeline.append(f"[{timestamp}] 🧠 Intelligence: score={data.get('lead_score', 0)}")
                
            elif event_type == "agent_routing":
                timeline.append(f"[{timestamp}] 🔀 Route: {data.get('from', '?')} → {data.get('to', '?')}")
                
            elif event_type == "tool_execution":
                timeline.append(f"[{timestamp}] 🔧 Tool: {data.get('tool_name', 'unknown')}")
                
            elif event_type == "message_sent":
                timeline.append(f"[{timestamp}] 📤 Sent: '{data.get('message', '')[:50]}...'")
                
            elif event_type == "error":
                timeline.append(f"[{timestamp}] ❌ ERROR: {data.get('error', 'unknown')}")
        
        return timeline
    
    def _generate_debug_hints(self, trace: Dict[str, Any]) -> List[str]:
        """Generate helpful debugging hints based on the trace"""
        hints = []
        
        # Check for common issues
        if trace["errors"]:
            hints.append("⚠️ Errors detected - check error details above")
        
        summary = trace["summary"]
        
        # Routing issues
        routing_path = summary.get("routing_path", [])
        if len(routing_path) > 2:
            hints.append("🔄 Multiple reroutings detected - possible routing loop")
        
        # Score issues
        if summary.get("lead_score", 0) == 0:
            hints.append("📊 Lead score is 0 - intelligence layer may not be extracting data")
        
        # Message issues
        if not summary.get("message_sent", False):
            hints.append("📭 No message sent - check responder node")
        
        # Duration issues
        if trace.get("duration_ms", 0) > 5000:
            hints.append("⏱️ Slow response (>5s) - check for API delays")
        
        return hints


# Global collector instance
_collector = TraceCollector()


def get_collector() -> TraceCollector:
    """Get the global trace collector instance"""
    return _collector


# Convenience functions
def start_trace(contact_id: str, webhook_data: Dict[str, Any]) -> str:
    """Start a new trace"""
    return _collector.start_trace(contact_id, webhook_data)


def trace_event(trace_id: str, event_type: str, data: Dict[str, Any], duration_ms: Optional[int] = None):
    """Add an event to the current trace"""
    _collector.add_event(trace_id, event_type, data, duration_ms)


def trace_error(trace_id: str, location: str, error: Exception, context: Dict[str, Any] = None):
    """Add an error to the current trace"""
    _collector.add_error(trace_id, location, error, context)


def end_trace(trace_id: str, final_state: Dict[str, Any] = None):
    """Complete the current trace"""
    _collector.end_trace(trace_id, final_state)


# Export functions
__all__ = [
    "TraceCollector",
    "get_collector",
    "start_trace",
    "trace_event", 
    "trace_error",
    "end_trace"
]