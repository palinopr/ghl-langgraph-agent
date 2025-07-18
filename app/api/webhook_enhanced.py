"""
Enhanced FastAPI webhook endpoint with streaming support
Receives webhooks and processes them through enhanced LangGraph workflow
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, AsyncIterator
import asyncio
import json
from app.workflow_v2 import run_workflow_v2
from app.tools.webhook_processor import webhook_processor
from app.tools.webhook_enricher import WebhookEnricher
from app.tools.supabase_client import supabase_client
from app.tools.ghl_client import ghl_client
from app.utils.message_batcher import MessageBatcher
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("webhook_enhanced")

# Create FastAPI app
app = FastAPI(
    title="GoHighLevel LangGraph Agent (Enhanced)",
    description="Enhanced webhook endpoint with streaming support",
    version="2.0.0"
)

# Initialize components
webhook_enricher = WebhookEnricher()
message_batcher = MessageBatcher()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ghl-langgraph-agent-enhanced",
        "features": ["streaming", "batching", "error_recovery", "parallel_processing"]
    }


@app.get("/health")
async def health_check():
    """Enhanced health check with component status"""
    try:
        # Check critical components
        components = {
            "api": "healthy",
            "supabase": "healthy" if supabase_client.client else "unavailable",
            "ghl": "healthy" if ghl_client else "unavailable",
            "batching": "enabled" if message_batcher else "disabled",
            "streaming": "enabled"
        }
        
        overall_status = "healthy" if all(
            status == "healthy" or status == "enabled" 
            for status in components.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "components": components
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}


@app.post("/webhook/message")
async def receive_message_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Enhanced webhook with batching and streaming support
    """
    try:
        # Parse webhook data
        webhook_data = await request.json()
        logger.info(f"Received webhook: {webhook_data.get('type', 'unknown')}")
        
        # Extract message data
        message_data = webhook_processor.extract_message_data(webhook_data)
        if not message_data:
            logger.warning("No message data found in webhook")
            return JSONResponse({"status": "no_message"}, status_code=200)
        
        # Check if it's from a bot
        if webhook_processor.is_from_bot(message_data):
            logger.info("Ignoring bot message")
            return JSONResponse({"status": "bot_ignored"}, status_code=200)
        
        # Enrich webhook data with full context
        enriched_data = await webhook_enricher.enrich_webhook_data(webhook_data)
        
        # Process with batching
        async def process_batched_message(messages):
            """Process batched messages through workflow"""
            try:
                # Merge messages for better context
                merged_content = webhook_enricher.merge_messages(messages)
                
                # Run enhanced workflow
                result = await run_workflow_v2(
                    contact_id=enriched_data.get("contact_id"),
                    message=merged_content,
                    context=enriched_data
                )
                
                logger.info("Workflow completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Error processing batched messages: {e}")
                raise
        
        # Add to batch and process
        batch_result = await message_batcher.add_message(
            contact_id=message_data.get("id"),
            message=message_data,
            process_callback=process_batched_message
        )
        
        # Queue response in background
        if batch_result and batch_result.get("messages"):
            background_tasks.add_task(
                send_response_to_ghl,
                contact_id=message_data.get("id"),
                messages=batch_result.get("messages", [])
            )
        
        return JSONResponse({
            "status": "queued",
            "batch_size": batch_result.get("batch_size", 1) if batch_result else 1,
            "contact_id": message_data.get("id")
        })
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/webhook/message/stream")
async def receive_message_webhook_streaming(
    request: Request
):
    """
    Streaming webhook endpoint for real-time responses
    """
    try:
        webhook_data = await request.json()
        message_data = webhook_processor.extract_message_data(webhook_data)
        
        if not message_data or webhook_processor.is_from_bot(message_data):
            return JSONResponse({"status": "ignored"}, status_code=200)
        
        # Enrich data
        enriched_data = await webhook_enricher.enrich_webhook_data(webhook_data)
        
        # Create streaming response
        async def stream_workflow_response():
            """Stream workflow responses"""
            try:
                # Import streaming workflow
                from app.workflow_enhanced import stream_enhanced_workflow
                
                # Stream responses
                async for event in stream_enhanced_workflow(
                    contact_id=enriched_data.get("contact_id"),
                    message=message_data.get("body", ""),
                    context=enriched_data
                ):
                    # Format as Server-Sent Events
                    if event["type"] == "token":
                        yield f"data: {json.dumps({'content': event['content']})}\n\n"
                    elif event["type"] == "tool_start":
                        yield f"data: {json.dumps({'tool': event['tool'], 'status': 'start'})}\n\n"
                    elif event["type"] == "tool_end":
                        yield f"data: {json.dumps({'tool': event['tool'], 'status': 'complete'})}\n\n"
                    
                # Send completion event
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            stream_workflow_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming webhook error: {str(e)}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


async def send_response_to_ghl(contact_id: str, messages: list):
    """
    Send response back to GoHighLevel with retries
    """
    from app.utils.error_recovery import with_retry, APIError
    
    @with_retry(max_attempts=3, initial_delay=1.0)
    async def send_with_retry():
        try:
            for message in messages:
                if hasattr(message, "content") and message.content:
                    await ghl_client.send_message(
                        contact_id=contact_id,
                        message=message.content
                    )
                    # Small delay between messages for natural feel
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"Failed to send message to GHL: {e}")
            raise APIError(f"GHL send failed: {e}")
    
    try:
        await send_with_retry()
        logger.info(f"Successfully sent {len(messages)} messages to GHL")
    except Exception as e:
        logger.error(f"Failed to send messages after retries: {e}")
        # Store failed messages for later retry
        await supabase_client.queue_message({
            "contact_id": contact_id,
            "messages": [m.content for m in messages if hasattr(m, "content")],
            "error": str(e),
            "retry_count": 3
        })


@app.post("/webhook/appointment")
async def receive_appointment_webhook(request: Request):
    """
    Handle appointment-related webhooks with streaming confirmation
    """
    try:
        webhook_data = await request.json()
        appointment_data = webhook_data.get("appointment", {})
        
        # Stream appointment confirmation
        from app.agents.sofia_agent_v2_enhanced import stream_appointment_confirmation
        
        async def stream_confirmation():
            async for token in stream_appointment_confirmation(
                contact_id=webhook_data.get("contactId"),
                appointment_details=appointment_data
            ):
                yield f"data: {json.dumps({'content': token})}\n\n"
            yield f"data: {json.dumps({'status': 'complete'})}\n\n"
        
        return StreamingResponse(
            stream_confirmation(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"Appointment webhook error: {e}")
        return JSONResponse({"status": "error"}, status_code=500)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize enhanced components on startup"""
    logger.info("Starting enhanced webhook service...")
    
    # Verify configurations
    settings = get_settings()
    logger.info(f"Environment: {settings.app_env}")
    logger.info("Streaming: Enabled")
    logger.info("Batching: Enabled")
    logger.info("Error Recovery: Enabled")
    logger.info("Parallel Processing: Enabled")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down enhanced webhook service...")
    await message_batcher.cleanup()


# Export for deployment
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.webhook_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )