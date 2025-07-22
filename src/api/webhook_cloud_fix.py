"""
Webhook handler that properly sets thread_id for LangGraph Cloud
This ensures conversation persistence by controlling thread_id at the API level
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
import httpx
import os
from app.utils.simple_logger import get_logger

logger = get_logger("webhook_cloud_fix")

app = FastAPI(
    title="GHL Webhook Handler for LangGraph Cloud",
    description="Ensures proper thread_id for conversation persistence",
    version="1.0.0"
)

# Configuration
LANGGRAPH_API_URL = os.getenv(
    "LANGGRAPH_API_URL", 
    "https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app"
)
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY")


@app.post("/webhook/message")
async def handle_ghl_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive webhook from GoHighLevel and invoke LangGraph with proper thread_id
    
    This handler ensures:
    1. Thread IDs are consistent based on contact/conversation
    2. Messages maintain conversation history
    3. Agents remember previous interactions
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received webhook: {webhook_data}")
        
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id"))
        conversation_id = webhook_data.get("conversationId")
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        
        if not contact_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing contact ID"}
            )
        
        # CRITICAL: Generate consistent thread_id
        # This is the key to fixing conversation persistence
        if conversation_id:
            thread_id = f"conv-{conversation_id}"
            logger.info(f"Using conversation-based thread_id: {thread_id}")
        else:
            thread_id = f"contact-{contact_id}"
            logger.info(f"Using contact-based thread_id: {thread_id}")
        
        # Add task to process in background
        background_tasks.add_task(
            invoke_langgraph_cloud,
            webhook_data=webhook_data,
            thread_id=thread_id,
            contact_id=contact_id,
            conversation_id=conversation_id
        )
        
        # Return immediate response to GHL
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "thread_id": thread_id,
                "message": "Webhook received and processing"
            }
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def invoke_langgraph_cloud(
    webhook_data: Dict[str, Any],
    thread_id: str,
    contact_id: str,
    conversation_id: str | None
):
    """
    Invoke LangGraph Cloud with proper configuration
    """
    try:
        # Prepare the input for LangGraph
        graph_input = {
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "thread_id": thread_id,  # Pass our thread_id in the input
            "conversation_id": conversation_id,
        }
        
        # CRITICAL: Set thread_id in the configuration
        # This is what LangGraph Cloud uses for checkpoint persistence
        config = {
            "configurable": {
                "thread_id": thread_id,  # This ensures checkpoint persistence!
            }
        }
        
        # Prepare the invocation request
        invocation_payload = {
            "input": graph_input,
            "config": config,
            "stream_mode": "values"  # or "updates" based on your needs
        }
        
        logger.info(f"Invoking LangGraph with thread_id: {thread_id}")
        logger.info(f"Invocation payload: {invocation_payload}")
        
        # Make the API call to LangGraph Cloud
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Content-Type": "application/json"}
            if LANGGRAPH_API_KEY:
                headers["Authorization"] = f"Bearer {LANGGRAPH_API_KEY}"
            
            # Use the correct endpoint for your deployment
            # Common patterns:
            # - /runs/invoke - for single invocation
            # - /runs/stream - for streaming responses
            # - /threads/{thread_id}/runs/stream - for thread-specific streaming
            
            response = await client.post(
                f"{LANGGRAPH_API_URL}/runs/invoke",
                json=invocation_payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ LangGraph invocation successful for thread: {thread_id}")
                logger.info(f"Response: {result}")
            else:
                logger.error(f"❌ LangGraph invocation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
    except Exception as e:
        logger.error(f"Error invoking LangGraph: {e}", exc_info=True)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "webhook-cloud-fix",
        "langgraph_url": LANGGRAPH_API_URL,
        "api_key_configured": bool(LANGGRAPH_API_KEY)
    }


@app.get("/")
async def root():
    """Root endpoint with instructions"""
    return {
        "service": "GHL Webhook Handler for LangGraph Cloud",
        "purpose": "Ensures proper thread_id for conversation persistence",
        "endpoints": {
            "/webhook/message": "POST - Receive GHL webhooks",
            "/health": "GET - Health check"
        },
        "configuration": {
            "LANGGRAPH_API_URL": "Set to your LangGraph Cloud deployment URL",
            "LANGGRAPH_API_KEY": "Set to your API key (if required)"
        }
    }


# Deployment Instructions:
"""
1. Deploy this as a separate service that sits between GHL and LangGraph Cloud
2. Configure environment variables:
   - LANGGRAPH_API_URL: Your LangGraph Cloud deployment URL
   - LANGGRAPH_API_KEY: Your API key (optional, depends on your setup)
3. Update GoHighLevel webhook URL to point to this service
4. This handler will ensure consistent thread_ids across all messages

Benefits:
- Conversation history is preserved
- Agents remember previous interactions
- No more repetitive questions
- Works with LangGraph Cloud's infrastructure
"""