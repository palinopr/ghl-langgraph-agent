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
from ..utils.logger import get_api_logger
from ..config import get_settings

logger = get_api_logger("webhook")

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
        
        # Process in background
        background_tasks.add_task(
            process_message_async,
            queue_entry["id"],
            message_data
        )
        
        # Return immediate acknowledgment
        return JSONResponse(
            status_code=200,
            content={
                "status": "received",
                "message_id": queue_entry["id"],
                "contact_id": message_data["contact_id"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


async def process_message_async(
    message_id: str,
    message_data: Dict[str, Any]
):
    """
    Process message asynchronously through LangGraph workflow
    
    Args:
        message_id: Queue message ID
        message_data: Processed message data
    """
    try:
        logger.info(f"Processing message {message_id} for contact {message_data['contact_id']}")
        
        # Update status to processing
        await supabase_client.update_message_status(
            message_id, 
            "processing"
        )
        
        # Get contact details from GHL
        contact_details = await ghl_client.get_contact_details(
            message_data["contact_id"]
        )
        
        # Get conversation history
        conversation_history = await ghl_client.get_conversation_history(
            message_data["contact_id"]
        )
        
        # Prepare context
        context = {
            "contact_details": contact_details,
            "conversation_history": conversation_history,
            "message_data": message_data
        }
        
        # Run workflow
        result = await run_workflow(
            contact_id=message_data["contact_id"],
            message=message_data["message_body"],
            context=context
        )
        
        # Extract agent response
        agent_responses = result.get("agent_responses", [])
        if agent_responses:
            last_response = agent_responses[-1]
            
            # Add to responder queue
            await supabase_client.add_to_responder_queue(
                contact_id=message_data["contact_id"],
                message_id=message_id,
                agent=last_response["agent"],
                response=last_response["response"],
                analysis=result.get("analysis", {})
            )
            
            # Send response via GHL
            send_result = await ghl_client.send_message(
                contact_id=message_data["contact_id"],
                message=last_response["response"],
                message_type=message_data.get("message_type", "WhatsApp")
            )
            
            if send_result:
                # Update message status to completed
                await supabase_client.update_message_status(
                    message_id,
                    "completed",
                    agent_name=last_response["agent"]
                )
                
                # If appointment was booked, update tracking
                if result.get("appointment_status") == "booked":
                    await supabase_client.mark_appointment_booked(
                        message_id,
                        result.get("appointment_id", "")
                    )
                
                logger.info(f"Successfully processed message {message_id}")
            else:
                raise Exception("Failed to send response via GHL")
        else:
            raise Exception("No agent response generated")
            
    except Exception as e:
        logger.error(f"Error processing message {message_id}: {str(e)}", exc_info=True)
        
        # Update status to failed
        await supabase_client.update_message_status(
            message_id,
            "failed",
            error_message=str(e)
        )


@app.post("/webhook/appointment")
async def receive_appointment_webhook(request: Request):
    """
    Receive appointment webhook from GoHighLevel
    
    Args:
        request: FastAPI request object
        
    Returns:
        Acknowledgment response
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received appointment webhook: {webhook_data}")
        
        # Process appointment update
        # This can be used to update conversation state, send confirmations, etc.
        
        return JSONResponse(
            status_code=200,
            content={"status": "received"}
        )
        
    except Exception as e:
        logger.error(f"Error processing appointment webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


# Background task to process queued messages
async def process_message_queue():
    """Background task to process pending messages from queue"""
    while True:
        try:
            # Get pending messages
            pending = await supabase_client.get_pending_messages(limit=5)
            
            for msg in pending:
                # Process each message
                await process_message_async(
                    msg["id"],
                    {
                        "contact_id": msg["contact_id"],
                        "message_body": msg["message"],
                        "message_type": msg.get("type", "WhatsApp"),
                        "location_id": msg.get("location_id"),
                        "conversation_id": msg.get("conversation_id")
                    }
                )
                
            # Wait before next check
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in queue processor: {str(e)}")
            await asyncio.sleep(10)


# Start background task on startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    asyncio.create_task(process_message_queue())
    logger.info("Started message queue processor")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)