"""
LangGraph Cloud Webhook Handler with Thread ID Fix
This handler ensures consistent thread_ids across messages
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Dict, Any
from app.utils.simple_logger import get_logger

logger = get_logger("langgraph_webhook")

# Get LangGraph Cloud configuration from environment
LANGGRAPH_API_URL = os.getenv("LANGGRAPH_API_URL", "https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app")
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY", "")

app = FastAPI(title="LangGraph Webhook Handler")


@app.post("/webhook/message")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook and invoke LangGraph with proper thread_id
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received webhook: {webhook_data}")
        
        # Extract contact ID
        contact_id = webhook_data.get("contactId", webhook_data.get("id"))
        if not contact_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing contact ID"}
            )
        
        # CRITICAL: Set consistent thread_id
        thread_id = f"contact-{contact_id}"
        conversation_id = webhook_data.get("conversationId")
        if conversation_id:
            thread_id = f"conv-{conversation_id}"
        
        logger.info(f"🔧 Setting thread_id: {thread_id} for contact: {contact_id}")
        
        # Prepare the invocation request with our thread_id
        invocation_request = {
            "input": {
                "messages": [],  # Will be populated by receptionist
                "webhook_data": webhook_data,
                "contact_id": contact_id,
                "thread_id": thread_id,
                # Include other needed fields
                "contact_name": webhook_data.get("contact_name", ""),
                "contact_email": webhook_data.get("contact_email", ""),
                "contact_phone": webhook_data.get("contact_phone", ""),
                "location_id": webhook_data.get("locationId", "sHFG9Rw6BdGh6d6bfMqG"),
                "conversation_id": conversation_id
            },
            "config": {
                "configurable": {
                    "thread_id": thread_id  # CRITICAL: Pass our thread_id here!
                }
            }
        }
        
        # Invoke LangGraph Cloud with our thread_id
        async with httpx.AsyncClient() as client:
            headers = {
                "Content-Type": "application/json"
            }
            if LANGGRAPH_API_KEY:
                headers["Authorization"] = f"Bearer {LANGGRAPH_API_KEY}"
            
            # Invoke the graph
            response = await client.post(
                f"{LANGGRAPH_API_URL}/runs/stream",
                json=invocation_request,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"LangGraph invocation failed: {response.status_code} - {response.text}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to invoke workflow"}
                )
            
            # Return success
            return JSONResponse(
                status_code=200,
                content={
                    "status": "accepted",
                    "thread_id": thread_id,
                    "message": "Webhook processed with consistent thread_id"
                }
            )
            
    except Exception as e:
        logger.error(f"Webhook handler error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "langgraph-webhook-handler",
        "langgraph_url": LANGGRAPH_API_URL,
        "has_api_key": bool(LANGGRAPH_API_KEY)
    }


# Instructions for deployment:
"""
1. Deploy this as a separate service or replace the existing webhook handler
2. Set environment variables:
   - LANGGRAPH_API_URL: Your LangGraph Cloud deployment URL
   - LANGGRAPH_API_KEY: Your API key (if required)
3. Point GoHighLevel webhooks to this handler
4. This handler will ensure consistent thread_ids across all messages
"""