#!/usr/bin/env python3
"""
Fixed GoHighLevel Webhook Handler
Properly acknowledges webhook and sends responses via GHL API
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "http://localhost:2024")
GHL_API_TOKEN = os.getenv("GHL_API_TOKEN")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")
GHL_API_URL = "https://services.leadconnectorhq.com"

# Initialize async clients
http_client: Optional[httpx.AsyncClient] = None
ghl_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global http_client, ghl_client
    http_client = httpx.AsyncClient(timeout=30.0)
    ghl_client = httpx.AsyncClient(
        base_url=GHL_API_URL,
        headers={
            "Authorization": f"Bearer {GHL_API_TOKEN}",
            "Version": "2021-07-28"
        },
        timeout=30.0
    )
    logger.info("Webhook server started")
    yield
    await http_client.aclose()
    await ghl_client.aclose()
    logger.info("Webhook server stopped")


# Create FastAPI app
app = FastAPI(
    title="GoHighLevel Webhook Handler (Fixed)",
    version="2.0.0",
    lifespan=lifespan
)


async def send_message_to_ghl(
    contact_id: str,
    message: str,
    conversation_id: Optional[str] = None
) -> bool:
    """Send message back to GoHighLevel via API"""
    try:
        # Split long messages
        messages = []
        if len(message) > 300:
            words = message.split()
            current = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > 300:
                    messages.append(' '.join(current))
                    current = [word]
                    current_length = len(word)
                else:
                    current.append(word)
                    current_length += len(word) + 1
            
            if current:
                messages.append(' '.join(current))
        else:
            messages = [message]
        
        # Send each message part
        for msg_part in messages:
            payload = {
                "type": "WhatsApp",
                "contactId": contact_id,
                "message": msg_part
            }
            
            response = await ghl_client.post(
                "/conversations/messages",
                json=payload
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to send message to GHL: {response.status_code} - {response.text}")
                return False
            
            # Small delay between messages if multiple
            if len(messages) > 1:
                await asyncio.sleep(0.5)
        
        logger.info(f"Successfully sent message to contact {contact_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending message to GHL: {str(e)}", exc_info=True)
        return False


async def process_message_async(
    contact_id: str,
    conversation_id: str,
    location_id: str,
    message_body: str,
    contact_data: Dict[str, Any]
):
    """Process message asynchronously and send response"""
    try:
        logger.info(f"Processing message from {contact_id}: {message_body[:50]}...")
        
        # Create thread ID from conversation ID
        thread_id = f"thread-{conversation_id}"
        
        # Prepare input for LangGraph
        input_data = {
            "messages": [{"role": "human", "content": message_body}],
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "location_id": location_id,
            "contact_name": f"{contact_data.get('firstName', '')} {contact_data.get('lastName', '')}"strip(),
            "email": contact_data.get("email", ""),
            "phone": contact_data.get("phone", ""),
            "thread_id": thread_id
        }
        
        # Add custom fields if available
        custom_fields = contact_data.get("customFields", {})
        if custom_fields:
            input_data["lead_score"] = int(custom_fields.get("wAPjuqxtfgKLCJqahjo1", "0") or "0")
            input_data["business_type"] = custom_fields.get("HtoheVc48qvAfvRUKhfG", "")
            input_data["last_intent"] = custom_fields.get("Q1n5kaciimUU6JN5PBD6", "")
        
        # Send to LangGraph
        ai_response = ""
        async with http_client.stream(
            "POST",
            f"{LANGGRAPH_URL}/threads/{thread_id}/runs/stream",
            json={
                "assistant_id": "agent",
                "input": input_data,
                "stream_mode": "updates"
            }
        ) as response:
            async for line in response.aiter_lines():
                if line and line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if isinstance(data, dict):
                            for node_name, node_data in data.items():
                                if isinstance(node_data, dict):
                                    if "final_response" in node_data:
                                        ai_response = node_data["final_response"]
                                    elif "messages" in node_data:
                                        for msg in reversed(node_data["messages"]):
                                            if isinstance(msg, dict) and msg.get("type") == "ai":
                                                ai_response = msg.get("content", "")
                                                break
                    except json.JSONDecodeError:
                        continue
        
        # Send response back to GHL
        if ai_response:
            await send_message_to_ghl(contact_id, ai_response, conversation_id)
        else:
            await send_message_to_ghl(
                contact_id, 
                "Lo siento, no pude procesar tu mensaje. Por favor intenta de nuevo.",
                conversation_id
            )
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await send_message_to_ghl(
            contact_id,
            "Disculpa, estoy teniendo problemas técnicos. Por favor intenta más tarde.",
            conversation_id
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "webhook-handler-fixed",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle incoming GoHighLevel webhooks"""
    try:
        # Parse payload
        payload = await request.json()
        webhook_type = payload.get("type", "")
        
        logger.info(f"Received webhook: {webhook_type}")
        
        # Only process inbound messages
        if webhook_type != "InboundMessage":
            return JSONResponse(
                content={"status": "accepted"},
                status_code=200
            )
        
        # Extract data
        contact_id = payload.get("contactId", "")
        conversation_id = payload.get("conversationId", "")
        location_id = payload.get("locationId", "")
        message_data = payload.get("message", {})
        contact_data = payload.get("contact", {})
        
        # Get message content
        message_body = message_data.get("body", "").strip()
        if not message_body:
            return JSONResponse(
                content={"error": "Empty message"},
                status_code=400
            )
        
        # Process message in background
        background_tasks.add_task(
            process_message_async,
            contact_id,
            conversation_id,
            location_id,
            message_body,
            contact_data
        )
        
        # Return immediate acknowledgment
        return JSONResponse(
            content={
                "status": "accepted",
                "message": "Webhook received and queued for processing"
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GoHighLevel Webhook Handler (Fixed)",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting webhook server on port {port}")
    logger.info(f"LangGraph URL: {LANGGRAPH_URL}")
    logger.info(f"GHL API URL: {GHL_API_URL}")
    logger.info(f"Webhook endpoint: http://localhost:{port}/webhook")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )