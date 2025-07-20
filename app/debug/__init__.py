"""
Debug Module for Workflow Tracing
Provides real-time trace collection for easier debugging
"""
from app.debug.trace_collector import (
    TraceCollector,
    get_collector,
    start_trace,
    trace_event,
    trace_error,
    end_trace
)
from app.debug.workflow_tracing import (
    trace_node,
    trace_tool,
    add_tracing_to_workflow,
    trace_workflow_event,
    trace_routing
)
from app.debug.trace_integration import add_workflow_tracing

__all__ = [
    # Collector functions
    "TraceCollector",
    "get_collector",
    "start_trace",
    "trace_event",
    "trace_error",
    "end_trace",
    
    # Decorators
    "trace_node",
    "trace_tool",
    
    # Integration
    "add_workflow_tracing",
    "add_tracing_to_workflow",
    
    # Helpers
    "trace_workflow_event",
    "trace_routing"
]