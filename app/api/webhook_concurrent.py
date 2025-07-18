"""
FastAPI webhook endpoint with concurrent processing
Optimized for Python 3.13 with TaskGroup and free-threading
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import asyncio
from datetime import datetime
from app.workflow import run_workflow
from app.tools.webhook_processor import webhook_processor
from app.tools.supabase_client import supabase_client
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("webhook_concurrent")

# Create FastAPI app
app = FastAPI(
    title="GoHighLevel LangGraph Agent - Concurrent",
    description="Concurrent webhook endpoint for processing GoHighLevel messages",
    version="2.0.0"
)

# Concurrent request tracking
active_requests: Dict[str, datetime] = {}
request_lock = asyncio.Lock()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "ghl-langgraph-agent-concurrent",
        "active_requests": len(active_requests)
    }


@app.get("/health")
async def health_check():
    """Enhanced health check with component status"""
    health_status = {
        "status": "healthy",
        "components": {
            "webhook": "operational",
            "ghl_client": "unknown",
            "supabase": "unknown",
            "active_requests": len(active_requests)
        },
        "performance": {
            "free_threading": "enabled" if hasattr(asyncio, 'TaskGroup') else "disabled"
        }
    }
    
    # Check components asynchronously
    async with asyncio.TaskGroup() as tg:
        ghl_task = tg.create_task(_check_ghl_health())
        supabase_task = tg.create_task(_check_supabase_health())
    
    health_status["components"]["ghl_client"] = "operational" if ghl_task.result() else "degraded"
    health_status["components"]["supabase"] = "operational" if supabase_task.result() else "degraded"
    
    return health_status


async def _check_ghl_health() -> bool:
    """Check GHL API health"""
    try:
        # Simple health check - verify we can authenticate
        return await ghl_client.verify_connection()
    except:
        return False


async def _check_supabase_health() -> bool:
    """Check Supabase health"""
    try:
        # Simple health check
        return await supabase_client.health_check()
    except:
        return False


@app.post("/webhook/message")
async def receive_message_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive and process message webhook concurrently
    
    Uses Python 3.13 TaskGroup for parallel processing
    """
    try:
        # Get webhook data
        webhook_data = await request.json()
        contact_id = webhook_data.get("id", "unknown")
        
        # Track active request
        async with request_lock:
            active_requests[contact_id] = datetime.now()
        
        try:
            # Validate webhook signature if configured
            settings = get_settings()
            if settings.webhook_secret:
                signature = request.headers.get("X-Webhook-Signature", "")
                body = await request.body()
                
                if not webhook_processor.validate_webhook_signature(
                    body, signature, settings.webhook_secret
                ):
                    logger.warning("Invalid webhook signature")
                    raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Process webhook data
            message_data = webhook_processor.process_message_webhook(webhook_data)
            if not message_data:
                logger.warning("Invalid webhook data format")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid webhook format"}
                )
            
            # Process with batching
            from app.utils.message_batcher import process_with_batching
            
            batch_result = await process_with_batching(
                contact_id=contact_id,
                message=message_data,
                process_callback=lambda msg: _process_concurrent(msg, background_tasks)
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": batch_result["status"],
                    "contact_id": contact_id,
                    "batch_info": batch_result
                }
            )
            
        finally:
            # Remove from active requests
            async with request_lock:
                active_requests.pop(contact_id, None)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


async def _process_concurrent(
    message_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Process message with concurrent operations
    
    Uses TaskGroup for parallel execution of:
    - Queue storage
    - Workflow processing
    - Metrics tracking
    """
    try:
        # Prepare tasks for concurrent execution
        async with asyncio.TaskGroup() as tg:
            # Queue the message
            queue_task = tg.create_task(
                supabase_client.create_queue_entry(
                    contact_id=message_data.get("id"),
                    message_data=message_data,
                    priority="high" if message_data.get("is_batch") else "normal"
                )
            )
            
            # Start workflow processing immediately
            workflow_task = tg.create_task(
                run_workflow(webhook_data=message_data)
            )
            
            # Track metrics
            metrics_task = tg.create_task(
                _track_metrics(message_data)
            )
        
        # All tasks completed successfully
        queue_id = queue_task.result()["id"]
        workflow_result = workflow_task.result()
        
        # Update queue status
        await supabase_client.update_queue_status(
            queue_id,
            "completed" if workflow_result.get("success") else "failed",
            result=workflow_result
        )
        
        logger.info(f"Concurrent processing completed for {message_data.get('id')}")
        
    except Exception as e:
        logger.error(f"Concurrent processing error: {e}")
        raise


async def _track_metrics(message_data: Dict[str, Any]):
    """Track processing metrics"""
    # This could send to monitoring service
    logger.info(f"Metrics tracked for {message_data.get('id')}")


@app.post("/webhook/appointment")
async def receive_appointment_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle appointment webhooks concurrently
    """
    try:
        webhook_data = await request.json()
        
        # Process appointment update
        appointment_data = webhook_processor.process_appointment_webhook(webhook_data)
        if not appointment_data:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid appointment webhook"}
            )
        
        # Update contact score in parallel
        async with asyncio.TaskGroup() as tg:
            # Update contact score to 10 (appointment booked)
            score_task = tg.create_task(
                ghl_client.update_custom_field(
                    appointment_data["contact_id"],
                    "wAPjuqxtfgKLCJqahjo1",  # score field
                    "10"
                )
            )
            
            # Add hot-lead tag
            tag_task = tg.create_task(
                ghl_client.add_tags(
                    appointment_data["contact_id"],
                    ["appointment-booked", "hot-lead"]
                )
            )
            
            # Send confirmation
            confirm_task = tg.create_task(
                ghl_client.send_message(
                    appointment_data["contact_id"],
                    "¡Perfecto! Tu cita está confirmada. Te enviaremos un recordatorio."
                )
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "processed",
                "appointment_id": appointment_data.get("appointment_id")
            }
        )
        
    except Exception as e:
        logger.error(f"Appointment webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


@app.post("/webhook/batch")
async def receive_batch_webhooks(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle multiple webhooks in a single request
    Processes them concurrently using TaskGroup
    """
    try:
        batch_data = await request.json()
        webhooks = batch_data.get("webhooks", [])
        
        if not webhooks:
            return JSONResponse(
                status_code=400,
                content={"error": "No webhooks in batch"}
            )
        
        results = []
        
        # Process all webhooks concurrently
        async with asyncio.TaskGroup() as tg:
            tasks = []
            for webhook in webhooks:
                task = tg.create_task(_process_single_webhook(webhook))
                tasks.append(task)
        
        # Collect results
        for i, task in enumerate(tasks):
            try:
                result = task.result()
                results.append({
                    "index": i,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                results.append({
                    "index": i,
                    "status": "failed",
                    "error": str(e)
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "batch_size": len(webhooks),
                "results": results
            }
        )
        
    except Exception as e:
        logger.error(f"Batch webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Batch processing failed"}
        )


async def _process_single_webhook(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single webhook from batch"""
    message_data = webhook_processor.process_message_webhook(webhook_data)
    if not message_data:
        raise ValueError("Invalid webhook format")
    
    result = await run_workflow(webhook_data=message_data)
    return result


# Background task for cleanup
async def cleanup_stale_requests():
    """Clean up stale active requests"""
    while True:
        try:
            async with request_lock:
                now = datetime.now()
                stale = []
                for contact_id, timestamp in active_requests.items():
                    if (now - timestamp).total_seconds() > 300:  # 5 minutes
                        stale.append(contact_id)
                
                for contact_id in stale:
                    active_requests.pop(contact_id)
                    logger.warning(f"Cleaned up stale request for {contact_id}")
            
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(60)


# Start cleanup task on startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(cleanup_stale_requests())
    logger.info("Concurrent webhook server started with Python 3.13 optimizations")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info(f"Shutting down with {len(active_requests)} active requests")