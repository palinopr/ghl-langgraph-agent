"""
FastAPI webhook endpoint for GoHighLevel messages
Receives webhooks and processes them through LangGraph workflow
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import asyncio
from ..workflow import run_workflow
from ..tools.webhook_processor import webhook_processor
from ..tools.supabase_client import supabase_client
from ..tools.ghl_client import ghl_client
from ..utils.simple_logger import get_logger
from ..config import get_settings

logger = get_logger("webhook")

# Create FastAPI app
app = FastAPI(
    title="GoHighLevel LangGraph Agent",
    description="Webhook endpoint for processing GoHighLevel messages",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ghl-langgraph-agent"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check Supabase connection
        await supabase_client.get_pending_messages(limit=1)
        supabase_status = "connected"
    except Exception as e:
        logger.error(f"Supabase health check failed: {e}")
        supabase_status = "error"
    
    return {
        "status": "healthy",
        "services": {
            "supabase": supabase_status,
            "langgraph": "ready"
        }
    }


@app.post("/webhook/message")
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
        
        # Add to message queue
        queue_entry = await supabase_client.add_to_message_queue(message_data)
        if not queue_entry:
            logger.error("Failed to add message to queue")
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to queue message"}
            )
        
        # Process message in background
        background_tasks.add_task(
            process_single_message,
            queue_entry["id"]
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
        
        # Run workflow
        result = await run_workflow(message["message_data"])
        
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