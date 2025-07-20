"""
FastAPI Middleware for Automatic Trace Collection
Captures all webhook requests and workflow execution
"""
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from app.debug.trace_collector import get_collector, start_trace, trace_event, trace_error, end_trace
from app.utils.simple_logger import get_logger

logger = get_logger("trace_middleware")


class TraceCollectorMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically collect traces for webhook requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only trace webhook endpoints
        if not request.url.path.startswith("/webhook"):
            return await call_next(request)
        
        start_time = time.time()
        trace_id = None
        
        try:
            # Read request body
            body = await request.body()
            request._body = body  # Store for later use
            
            # Parse webhook data
            webhook_data = {}
            if body:
                try:
                    webhook_data = json.loads(body)
                except:
                    webhook_data = {"raw": body.decode("utf-8", errors="ignore")}
            
            # Get contact ID
            contact_id = webhook_data.get("contactId", "unknown")
            
            # Start trace
            trace_id = start_trace(contact_id, webhook_data)
            
            # Store trace ID in request state for access in routes
            request.state.trace_id = trace_id
            
            # Log webhook received
            trace_event(trace_id, "webhook_received", {
                "path": request.url.path,
                "method": request.method,
                "message": webhook_data.get("body", ""),
                "contact_id": contact_id
            })
            
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log completion
            trace_event(trace_id, "webhook_completed", {
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }, duration_ms)
            
            # End trace
            end_trace(trace_id, {
                "status_code": response.status_code,
                "success": response.status_code < 400
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error in trace middleware: {str(e)}", exc_info=True)
            
            if trace_id:
                trace_error(trace_id, "middleware", e, {
                    "path": request.url.path,
                    "method": request.method
                })
                end_trace(trace_id, {"error": str(e)})
            
            # Re-raise to let FastAPI handle the error
            raise


def inject_trace_id(state: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
    """Inject trace ID into workflow state"""
    state["_trace_id"] = trace_id
    return state


def get_trace_id_from_state(state: Dict[str, Any]) -> str:
    """Get trace ID from workflow state"""
    return state.get("_trace_id", "unknown")