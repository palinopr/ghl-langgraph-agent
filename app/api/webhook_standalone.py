"""
Standalone webhook handler for LangGraph Cloud thread persistence
No dependencies on local modules - completely self-contained
"""
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import httpx
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "agent")


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
            logger.error("Missing contact ID in webhook")
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
            conversation_id=conversation_id,
            message_body=message_body
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
    conversation_id: Optional[str],
    message_body: str
):
    """
    Invoke LangGraph Cloud with proper configuration
    """
    try:
        # Prepare the input for LangGraph
        # This matches the expected format from your workflow
        graph_input = {
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "thread_id": thread_id,
            "conversation_id": conversation_id,
            "messages": [],  # Will be populated by receptionist
            "lead_score": 0,
            "extracted_data": {},
            "is_new_conversation": True,
            "conversation_stage": "initial",
            "location_id": webhook_data.get("locationId", ""),
            "should_end": False,
            "needs_escalation": False,
            "supervisor_complete": False,
            "message_sent": False
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
            "assistant_id": ASSISTANT_ID,
            "stream_mode": "values"
        }
        
        logger.info(f"Invoking LangGraph with thread_id: {thread_id}")
        logger.info(f"Message: {message_body}")
        
        # Make the API call to LangGraph Cloud
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": LANGGRAPH_API_KEY
            }
            
            # Use the runs endpoint which works with LangGraph Cloud
            invoke_url = f"{LANGGRAPH_API_URL}/runs"
            
            response = await client.post(
                invoke_url,
                json={
                    "assistant_id": ASSISTANT_ID,
                    "input": graph_input,
                    "config": config
                },
                headers=headers
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                logger.info(f"✅ LangGraph invocation successful for thread: {thread_id}")
                logger.info(f"Run ID: {result.get('run_id', 'N/A')}")
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
        "service": "webhook-standalone",
        "langgraph_url": LANGGRAPH_API_URL,
        "assistant_id": ASSISTANT_ID,
        "api_key_configured": bool(LANGGRAPH_API_KEY),
        "timestamp": datetime.now().isoformat()
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
            "LANGGRAPH_API_URL": LANGGRAPH_API_URL,
            "ASSISTANT_ID": ASSISTANT_ID,
            "api_key_configured": bool(LANGGRAPH_API_KEY)
        }
    }


@app.post("/test")
async def test_endpoint(request: Request):
    """Test endpoint to verify webhook processing"""
    data = await request.json()
    return {
        "received": data,
        "thread_id_would_be": f"conv-{data.get('conversationId')}" if data.get('conversationId') else f"contact-{data.get('contactId', 'unknown')}"
    }