"""
Debug API Endpoints for Trace Collection
Easy access to traces for debugging
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import json
import asyncio
import os
from datetime import datetime
from app.debug.trace_collector import get_collector
from app.utils.simple_logger import get_logger

logger = get_logger("debug_endpoints")

# Create router
debug_router = APIRouter(prefix="/debug", tags=["debug"])


@debug_router.get("/health")
async def debug_health():
    """Check if debug endpoints are working"""
    collector = get_collector()
    return {
        "status": "ok",
        "total_traces": len(collector.traces),
        "active_traces": len(collector.active_traces),
        "error_traces": len(collector.error_traces),
        "timestamp": datetime.now().isoformat()
    }


@debug_router.get("/traces")
async def list_traces(
    limit: int = Query(20, description="Number of traces to return"),
    contact_id: Optional[str] = Query(None, description="Filter by contact ID"),
    status: Optional[str] = Query(None, description="Filter by status (completed/error)")
):
    """List recent traces"""
    collector = get_collector()
    
    if contact_id:
        traces = collector.get_traces_for_contact(contact_id, limit)
    else:
        # Get all traces
        all_traces = list(collector.traces)[-limit:]
        
        # Filter by status if provided
        if status:
            traces = [t for t in all_traces if t.get("status") == status]
        else:
            traces = all_traces
    
    return {
        "count": len(traces),
        "traces": [
            {
                "trace_id": t["trace_id"],
                "contact_id": t["contact_id"],
                "started_at": t["started_at"],
                "duration_ms": t.get("duration_ms"),
                "status": t["status"],
                "message": t["webhook_data"]["message"][:50] + "..." if len(t["webhook_data"]["message"]) > 50 else t["webhook_data"]["message"],
                "errors": len(t["errors"]),
                "events": len(t["events"])
            }
            for t in traces
        ]
    }


@debug_router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace by ID"""
    collector = get_collector()
    trace = collector.get_trace(trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return trace


@debug_router.get("/trace/{trace_id}/export")
async def export_trace(trace_id: str):
    """Export trace in debugging-friendly format"""
    collector = get_collector()
    export = collector.export_trace_for_debugging(trace_id)
    
    return JSONResponse(
        content=json.loads(export),
        headers={
            "Content-Disposition": f"attachment; filename=trace_{trace_id}.json"
        }
    )


@debug_router.get("/last-trace")
async def get_last_trace():
    """Get the most recent trace"""
    collector = get_collector()
    trace = collector.get_last_trace()
    
    if not trace:
        raise HTTPException(status_code=404, detail="No traces found")
    
    return trace


@debug_router.get("/last-error")
async def get_last_error():
    """Get the most recent trace with errors"""
    collector = get_collector()
    trace = collector.get_last_error_trace()
    
    if not trace:
        return {"message": "No error traces found", "status": "success"}
    
    # Format for easy debugging
    return {
        "trace_id": trace["trace_id"],
        "contact_id": trace["contact_id"],
        "error_summary": {
            "count": len(trace["errors"]),
            "first_error": trace["errors"][0] if trace["errors"] else None,
            "locations": [e["location"] for e in trace["errors"]]
        },
        "timeline": collector._create_timeline(trace),
        "export_command": f"curl http://localhost:8000/debug/trace/{trace['trace_id']}/export",
        "full_trace": trace
    }


@debug_router.get("/active")
async def get_active_traces():
    """Get currently active traces (still running)"""
    collector = get_collector()
    active = collector.get_active_traces()
    
    return {
        "count": len(active),
        "traces": [
            {
                "trace_id": t["trace_id"],
                "contact_id": t["contact_id"],
                "started_at": t["started_at"],
                "events_so_far": len(t["events"]),
                "current_status": t["status"]
            }
            for t in active
        ]
    }


@debug_router.get("/stream")
async def stream_traces():
    """Stream traces in real-time (Server-Sent Events)"""
    async def event_generator():
        """Generate SSE events for new traces"""
        seen_traces = set()
        
        while True:
            collector = get_collector()
            
            # Check for new traces
            for trace in list(collector.traces)[-10:]:  # Last 10 traces
                trace_id = trace["trace_id"]
                if trace_id not in seen_traces:
                    seen_traces.add(trace_id)
                    
                    # Format as SSE event
                    event_data = {
                        "trace_id": trace_id,
                        "contact_id": trace["contact_id"],
                        "message": trace["webhook_data"]["message"],
                        "status": trace["status"],
                        "duration_ms": trace.get("duration_ms"),
                        "timestamp": trace["started_at"]
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
            
            # Also check active traces
            for trace in collector.active_traces.values():
                event_data = {
                    "trace_id": trace["trace_id"],
                    "contact_id": trace["contact_id"],
                    "status": "active",
                    "events": len(trace["events"]),
                    "type": "active_trace"
                }
                yield f"data: {json.dumps(event_data)}\n\n"
            
            # Wait before next check
            await asyncio.sleep(1)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@debug_router.post("/clear")
async def clear_traces(keep_errors: bool = Query(True, description="Keep error traces")):
    """Clear trace history (useful for testing)"""
    collector = get_collector()
    
    with collector.lock:
        cleared = len(collector.traces)
        collector.traces.clear()
        
        if not keep_errors:
            collector.error_traces.clear()
    
    return {
        "message": f"Cleared {cleared} traces",
        "kept_errors": keep_errors
    }


@debug_router.get("/stats")
async def get_trace_stats():
    """Get statistics about traces"""
    collector = get_collector()
    
    # Calculate stats
    total_traces = len(collector.traces)
    error_traces = sum(1 for t in collector.traces if t["errors"])
    
    # Average duration
    durations = [t.get("duration_ms", 0) for t in collector.traces if t.get("duration_ms")]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Agent routing stats
    agent_counts = {}
    for trace in collector.traces:
        for path in trace.get("summary", {}).get("routing_path", []):
            if "→" in path:
                agent = path.split("→")[1].strip()
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
    
    return {
        "total_traces": total_traces,
        "error_traces": error_traces,
        "error_rate": f"{(error_traces / total_traces * 100):.1f}%" if total_traces > 0 else "0%",
        "average_duration_ms": int(avg_duration),
        "agent_routing": agent_counts,
        "active_traces": len(collector.active_traces)
    }


# Create convenience endpoint for quick debugging
@debug_router.get("/quick-debug/{contact_id}")
async def quick_debug(contact_id: str):
    """Get everything needed to debug issues for a contact"""
    collector = get_collector()
    
    # Get recent traces for this contact
    traces = collector.get_traces_for_contact(contact_id, limit=5)
    
    if not traces:
        raise HTTPException(status_code=404, detail=f"No traces found for contact {contact_id}")
    
    # Get the most recent trace details
    latest_trace = traces[0]
    
    return {
        "contact_id": contact_id,
        "recent_traces": len(traces),
        "latest_trace": {
            "trace_id": latest_trace["trace_id"],
            "timeline": collector._create_timeline(latest_trace),
            "errors": latest_trace["errors"],
            "summary": latest_trace["summary"],
            "debug_hints": collector._generate_debug_hints(latest_trace)
        },
        "export_commands": {
            "latest": f"curl http://localhost:8000/debug/trace/{latest_trace['trace_id']}/export",
            "all": f"curl http://localhost:8000/debug/traces?contact_id={contact_id}"
        }
    }


# Export router
__all__ = ["debug_router"]