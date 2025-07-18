"""
FastAPI webhook endpoint for GoHighLevel messages
Receives webhooks and processes them through LangGraph workflow
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
from app.workflow import run_workflow
from app.tools.webhook_processor import webhook_processor
from app.tools.supabase_client import supabase_client
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.performance_monitor import track_performance, get_performance_monitor, start_performance_monitoring

logger = get_logger("webhook")

# Create FastAPI app
app = FastAPI(
    title="GoHighLevel LangGraph Agent",
    description="Webhook endpoint for processing GoHighLevel messages with Python 3.13 optimizations",
    version="2.0.0"
)

# Initialize performance monitoring on startup
@app.on_event("startup")
async def startup_event():
    """Initialize performance monitoring on startup"""
    await start_performance_monitoring()
    logger.info("Performance monitoring initialized")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ghl-langgraph-agent"}


@app.get("/health")
async def health_check():
    """Health check with performance metrics"""
    monitor = get_performance_monitor()
    return {
        "status": "healthy",
        "optimizations": monitor.check_python_optimizations()
    }

@app.get("/performance")
async def performance_metrics():
    """Get detailed performance metrics"""
    monitor = get_performance_monitor()
    return monitor.get_performance_summary()


@app.post("/webhook/message")
@track_performance
async def receive_message_webhook(
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
        logger.info(f"Received webhook: {webhook_data}")
        
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
        
        # Use message batching for human-like responses
        from app.utils.message_batcher import process_with_batching
        
        batch_result = await process_with_batching(
            contact_id=message_data.get("id", "unknown"),
            message=message_data,
            process_callback=lambda msg: process_batched_message(msg, background_tasks)
        )
        
        if batch_result["status"] == "batching":
            logger.info(
                f"Message batched for {message_data.get('id')}, "
                f"waiting {batch_result['wait_time']}s for more messages"
            )
        
        # Return immediate acknowledgment
        return JSONResponse(
            status_code=200,
            content={
                "status": "queued",
                "queue_id": queue_entry["id"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


@track_performance
async def process_single_message(queue_id: str):
    """
    Process a single message from the queue
    
    Args:
        queue_id: Queue entry ID
    """
    try:
        # Get message from queue
        message = await supabase_client.get_queue_entry(queue_id)
        if not message:
            logger.error(f"Queue entry not found: {queue_id}")
            return
        
        # Update status to processing
        await supabase_client.update_queue_status(
            queue_id,
            "processing"
        )
        
        # Run workflow with full webhook data
        result = await run_workflow(webhook_data=message["message_data"])
        
        # Update status based on result
        if result.get("success"):
            await supabase_client.update_queue_status(
                queue_id,
                "completed",
                result=result
            )
        else:
            await supabase_client.update_queue_status(
                queue_id,
                "failed",
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        logger.error(f"Message processing error: {e}")
        await supabase_client.update_queue_status(
            queue_id,
            "failed",
            error=str(e)
        )


async def process_message_queue():
    """
    Process pending messages from the queue
    Called by the worker process
    """
    logger.info("Starting message queue processor")
    
    while True:
        try:
            # Get pending messages
            messages = await supabase_client.get_pending_messages(limit=5)
            
            if messages:
                logger.info(f"Processing {len(messages)} messages")
                
                # Process each message
                for message in messages:
                    await process_single_message(message["id"])
            
            # Wait before next check
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
            await asyncio.sleep(10)  # Wait longer on error


@track_performance
async def process_batched_message(
    message_data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Process a batched message (possibly multiple messages merged)
    
    Args:
        message_data: Message data with merged content
        background_tasks: FastAPI background task manager
    """
    # Add to message queue
    queue_entry = await supabase_client.add_to_message_queue(message_data)
    if not queue_entry:
        logger.error("Failed to add batched message to queue")
        return
    
    # Process message in background
    background_tasks.add_task(
        process_single_message,
        queue_entry["id"]
    )