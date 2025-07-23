"""
LangGraph Cloud Webhook Handler for GoHighLevel Integration
Ensures proper thread persistence by intercepting webhooks and 
invoking LangGraph Cloud with consistent thread_ids.
"""
import os
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
LANGGRAPH_API_URL = os.getenv("LANGGRAPH_API_URL", "https://api.smith.langchain.com")
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY")
LANGGRAPH_DEPLOYMENT_URL = os.getenv("LANGGRAPH_DEPLOYMENT_URL")
ASSISTANT_ID = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")

# Initialize FastAPI app
app = FastAPI(title="LangGraph Cloud Webhook Handler")

# Initialize LangGraph client
if not LANGGRAPH_API_KEY:
    logger.warning("LANGGRAPH_API_KEY not set - client initialization will fail")
    
langgraph_client: Optional[LangGraphClient] = None
try:
    # Use deployment URL if available, otherwise fall back to API URL
    client_url = LANGGRAPH_DEPLOYMENT_URL or LANGGRAPH_API_URL
    langgraph_client = get_client(url=client_url, api_key=LANGGRAPH_API_KEY)
    logger.info(f"LangGraph client initialized with URL: {client_url}")
except Exception as e:
    logger.error(f"Failed to initialize LangGraph client: {e}")


def generate_thread_id(webhook_data: Dict[str, Any]) -> str:
    """
    Generate consistent thread_id from webhook data.
    
    Priority:
    1. If conversationId exists: use conv-{conversationId}
    2. Otherwise: use contact-{contactId}
    
    Args:
        webhook_data: The webhook payload from GoHighLevel
        
    Returns:
        str: The generated thread_id
    """
    # Try to extract conversationId first
    conversation_id = webhook_data.get("conversationId")
    if conversation_id:
        return f"conv-{conversation_id}"
    
    # Fallback to contactId
    contact_id = webhook_data.get("contactId")
    if contact_id:
        return f"contact-{contact_id}"
    
    # If neither exists, raise an error
    raise ValueError("No conversationId or contactId found in webhook data")


async def process_webhook_async(
    thread_id: str,
    webhook_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process webhook asynchronously by invoking LangGraph Cloud.
    
    Args:
        thread_id: The consistent thread identifier
        webhook_data: The webhook payload to process
        
    Returns:
        Dict containing the processing result
    """
    if not langgraph_client:
        raise RuntimeError("LangGraph client not initialized")
    
    try:
        # Prepare the configuration with thread_id
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        # Log the invocation details
        logger.info(f"Invoking LangGraph Cloud with thread_id: {thread_id}")
        logger.debug(f"Config: {config}")
        logger.debug(f"Input data: {webhook_data}")
        
        # Stream the run results
        response_chunks = []
        async for chunk in langgraph_client.runs.stream(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            input=webhook_data,
            config=config,
            stream_mode=["values", "updates", "debug"]
        ):
            response_chunks.append(chunk)
            logger.debug(f"Received chunk: {chunk}")
        
        # Process the response
        result = {
            "thread_id": thread_id,
            "assistant_id": ASSISTANT_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "chunks_received": len(response_chunks),
            "status": "completed"
        }
        
        # Extract the final output if available
        if response_chunks:
            # Look for the final values in the stream
            for chunk in reversed(response_chunks):
                if isinstance(chunk, dict) and "values" in chunk:
                    result["output"] = chunk["values"]
                    break
        
        logger.info(f"Successfully processed webhook for thread_id: {thread_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise


@app.post("/webhook/message")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Main webhook endpoint for GoHighLevel messages.
    
    Receives webhooks, generates consistent thread_ids, and invokes
    LangGraph Cloud with proper configuration for thread persistence.
    """
    try:
        # Parse webhook data
        webhook_data = await request.json()
        logger.info(f"Received webhook: {webhook_data.get('type', 'unknown')}")
        
        # Generate consistent thread_id
        thread_id = generate_thread_id(webhook_data)
        logger.info(f"Generated thread_id: {thread_id}")
        
        # Process webhook asynchronously
        # We use background tasks to return quickly to GHL
        background_tasks.add_task(
            process_webhook_async,
            thread_id,
            webhook_data
        )
        
        # Return immediate response to GoHighLevel
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "thread_id": thread_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except ValueError as e:
        logger.error(f"Invalid webhook data: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid webhook data",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Webhook handling error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "Failed to process webhook"
            }
        )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "langgraph_client": langgraph_client is not None,
        "api_url": LANGGRAPH_API_URL,
        "assistant_id": ASSISTANT_ID,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with basic info."""
    return {
        "service": "LangGraph Cloud Webhook Handler",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook/message",
            "health": "/health"
        }
    }


# Optional: Direct invocation endpoint for testing
@app.post("/invoke/{thread_id}")
async def direct_invoke(
    thread_id: str,
    request: Request
) -> JSONResponse:
    """
    Direct invocation endpoint for testing thread persistence.
    
    Args:
        thread_id: The thread identifier to use
        request: The request containing the input data
    """
    try:
        input_data = await request.json()
        result = await process_webhook_async(thread_id, input_data)
        
        return JSONResponse(
            status_code=200,
            content=result
        )
    except Exception as e:
        logger.error(f"Direct invocation error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Invocation failed",
                "message": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )