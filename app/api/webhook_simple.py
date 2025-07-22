"""
Simple FastAPI webhook endpoint for GoHighLevel messages
Works without Supabase dependency
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
from app.workflow import run_workflow
from app.tools.webhook_processor import webhook_processor
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.config import get_settings
import time
import psutil
import platform

logger = get_logger("webhook")

# Create FastAPI app
app = FastAPI(
    title="GoHighLevel LangGraph Agent",
    description="Webhook endpoint for processing GoHighLevel messages",
    version="3.0.7"
)

# Store start time for uptime calculation
app.state.start_time = time.time()



@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ghl-langgraph-agent"}


@app.get("/test-debug")
async def test_debug():
    """Test endpoint"""
    return {"test": "debug works"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ghl-langgraph-agent",
        "debug_enabled": True,
        "trace_collector": "active",
        "version": "3.0.7",
        "python_version": "3.13"
    }


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    # Get process stats
    process = psutil.Process()
    memory_info = process.memory_info()
    
    # Get system stats
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    # Get workflow metrics from trace collector if available
    workflow_metrics = {}
    if hasattr(app.state, "trace_collector"):
        recent_traces = app.state.trace_collector.get_recent_traces(minutes=5)
        successful = sum(1 for t in recent_traces if not t.get("error"))
        failed = sum(1 for t in recent_traces if t.get("error"))
        
        workflow_metrics = {
            "workflows_last_5min": len(recent_traces),
            "workflows_successful": successful,
            "workflows_failed": failed,
            "success_rate": successful / len(recent_traces) if recent_traces else 0
        }
    
    return {
        "service": "ghl-langgraph-agent",
        "timestamp": int(time.time()),
        "uptime_seconds": int(time.time() - app.state.start_time) if hasattr(app.state, "start_time") else 0,
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent
        },
        "process": {
            "memory_mb": memory_info.rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads()
        },
        "workflow": workflow_metrics
    }


@app.get("/ok")
async def ok():
    """Simple health check endpoint (LangGraph standard)"""
    return {"ok": True}


@app.post("/webhook/message")
async def message_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive message webhook from GoHighLevel
    
    Args:
        request: FastAPI request object
        background_tasks: Background task manager
        
    Returns:
        Acknowledgment response
    """
    try:
        # Get webhook data
        webhook_data = await request.json()
        logger.info(
            "Webhook received",
            contact_id=webhook_data.get("contactId"),
            conversation_id=webhook_data.get("conversationId"),
            webhook_type=webhook_data.get("type", "message"),
            has_body=bool(webhook_data.get("body"))
        )
        
        # Validate webhook has required fields
        if not webhook_data.get("contactId") and not webhook_data.get("id"):
            logger.warning("Invalid webhook - missing contact ID", webhook_data=webhook_data)
            return JSONResponse(
                status_code=400,
                content={"error": "Missing contact ID"}
            )
        
        # Get trace ID from request if available
        trace_id = getattr(request.state, "trace_id", None)
        if trace_id:
            webhook_data["__trace_id__"] = trace_id
        
        # Process webhook in background for quick response
        background_tasks.add_task(process_message_async, webhook_data)
        
        # Return immediate acknowledgment
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Webhook received and queued for processing",
                "trace_id": trace_id
            }
        )
        
    except Exception as e:
        logger.error("Webhook processing error", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def process_message_async(webhook_data: Dict[str, Any]):
    """
    Process message asynchronously
    
    Args:
        webhook_data: Webhook data from GHL
    """
    try:
        logger.info(
            "Processing message async",
            contact_id=webhook_data.get('contactId', 'unknown'),
            conversation_id=webhook_data.get('conversationId'),
            trace_id=webhook_data.get('__trace_id__')
        )
        
        # Run the workflow
        result = await run_workflow(webhook_data)
        
        if result.get("success"):
            logger.info(
                "Message processed successfully",
                contact_id=webhook_data.get('contactId'),
                success=True,
                result=result
            )
        else:
            logger.error(
                "Message processing failed",
                contact_id=webhook_data.get('contactId'),
                success=False,
                result=result
            )
            
    except Exception as e:
        logger.error(
            "Async processing error",
            contact_id=webhook_data.get('contactId'),
            error=str(e),
            exc_info=True
        )


@app.post("/webhook/contact")
async def contact_webhook(request: Request):
    """Handle contact update webhooks"""
    webhook_data = await request.json()
    logger.info("Contact webhook received", webhook_type=webhook_data.get('type', 'unknown'), contact_id=webhook_data.get('contactId'))
    return {"status": "ok"}


@app.post("/webhook/appointment")  
async def appointment_webhook(request: Request):
    """Handle appointment webhooks"""
    webhook_data = await request.json()
    logger.info("Appointment webhook received", webhook_type=webhook_data.get('type', 'unknown'), appointment_id=webhook_data.get('id'))
    return {"status": "ok"}


# Export app for uvicorn
__all__ = ["app"]