#!/usr/bin/env python3
"""
Production Webhook Handler for GoHighLevel Integration
Handles incoming webhooks and routes to LangGraph
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
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
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize async client
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global http_client
    http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("Webhook server started")
    yield
    await http_client.aclose()
    logger.info("Webhook server stopped")


# Create FastAPI app
app = FastAPI(
    title="GoHighLevel Webhook Handler",
    version="1.0.0",
    lifespan=lifespan
)


class WebhookPayload(BaseModel):
    """GoHighLevel webhook payload structure"""
    type: str
    locationId: str
    contactId: str
    conversationId: str
    message: Dict[str, Any]
    contact: Dict[str, Any]


class ConversationManager:
    """Manages conversation history with database"""
    
    @staticmethod
    async def load_conversation_history(contact_id: str, conversation_id: str) -> list:
        """Load conversation history from database"""
        # TODO: Implement Supabase query
        # For now, return empty list - in production, load from database
        logger.info(f"Loading history for conversation {conversation_id}")
        return []
    
    @staticmethod
    async def save_conversation_history(
        contact_id: str, 
        conversation_id: str, 
        messages: list,
        metadata: Dict[str, Any]
    ):
        """Save conversation history to database"""
        # TODO: Implement Supabase insert/update
        logger.info(f"Saving history for conversation {conversation_id}")
        pass


async def send_to_langgraph(
    messages: list,
    contact_id: str,
    conversation_id: str,
    location_id: str,
    contact_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Send conversation to LangGraph and get response"""
    try:
        # Create thread ID from conversation ID for consistency
        thread_id = f"thread-{conversation_id}"
        
        # Prepare input
        input_data = {
            "messages": messages,
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "location_id": location_id,
            "contact_name": f"{contact_data.get('firstName', '')} {contact_data.get('lastName', '')}".strip(),
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
        
        logger.info(f"Sending to LangGraph with thread {thread_id}")
        
        # First, try to create/get thread
        thread_response = await http_client.post(
            f"{LANGGRAPH_URL}/threads",
            json={"thread_id": thread_id}
        )
        
        if thread_response.status_code not in [200, 201]:
            logger.warning(f"Thread creation returned {thread_response.status_code}")
        
        # Stream the response
        final_state = None
        current_agent = "unknown"
        lead_score = 0
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
                if line:
                    try:
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            if data and isinstance(data, dict):
                                final_state = data
                    except json.JSONDecodeError:
                        continue
        
        # Extract response from final state
        if final_state:
            for node_name, node_data in final_state.items():
                if isinstance(node_data, dict):
                    if node_name in ["maria", "carlos", "sofia"]:
                        current_agent = node_name
                    
                    if "lead_score" in node_data:
                        lead_score = node_data["lead_score"]
                    
                    if "messages" in node_data:
                        for msg in reversed(node_data["messages"]):
                            if isinstance(msg, dict) and msg.get("type") == "ai":
                                ai_response = msg.get("content", "")
                                break
                    
                    if "final_response" in node_data:
                        ai_response = node_data["final_response"]
        
        return {
            "success": True,
            "message": ai_response or "Lo siento, no pude procesar tu mensaje. Por favor intenta de nuevo.",
            "agent": current_agent,
            "lead_score": lead_score,
            "thread_id": thread_id
        }
        
    except Exception as e:
        logger.error(f"LangGraph error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": "Disculpa, estoy teniendo problemas técnicos. Por favor intenta más tarde.",
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "webhook-handler",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle incoming GoHighLevel webhooks"""
    try:
        # Verify webhook secret if configured
        if WEBHOOK_SECRET:
            signature = request.headers.get("X-GHL-Signature", "")
            # TODO: Implement signature verification
        
        # Parse payload
        payload = await request.json()
        webhook_type = payload.get("type", "")
        
        logger.info(f"Received webhook: {webhook_type}")
        
        # Only process inbound messages
        if webhook_type != "InboundMessage":
            return JSONResponse(
                content={"success": True, "message": "Webhook received"},
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
                content={"success": False, "error": "Empty message"},
                status_code=400
            )
        
        logger.info(f"Processing message from {contact_id}: {message_body[:50]}...")
        
        # Load conversation history
        conversation_history = await ConversationManager.load_conversation_history(
            contact_id, conversation_id
        )
        
        # Add new message to history
        conversation_history.append({
            "role": "human",
            "content": message_body
        })
        
        # Send to LangGraph
        result = await send_to_langgraph(
            messages=conversation_history,
            contact_id=contact_id,
            conversation_id=conversation_id,
            location_id=location_id,
            contact_data=contact_data
        )
        
        # Add AI response to history
        if result["success"] and result["message"]:
            conversation_history.append({
                "role": "ai",
                "content": result["message"]
            })
            
            # Save updated history in background
            background_tasks.add_task(
                ConversationManager.save_conversation_history,
                contact_id,
                conversation_id,
                conversation_history,
                {
                    "agent": result.get("agent"),
                    "lead_score": result.get("lead_score"),
                    "thread_id": result.get("thread_id")
                }
            )
        
        # Prepare response with custom field updates
        response_data = {
            "success": result["success"],
            "message": result["message"],
            "agent": result.get("agent", "unknown"),
            "custom_fields": {}
        }
        
        # Update lead score if changed
        if result.get("lead_score", 0) > 0:
            response_data["custom_fields"]["wAPjuqxtfgKLCJqahjo1"] = str(result["lead_score"])
        
        # Log success
        logger.info(f"Successfully processed message for {contact_id}")
        
        return JSONResponse(content=response_data, status_code=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "success": False,
                "error": "Internal server error",
                "message": "Lo siento, hubo un error. Por favor intenta más tarde."
            },
            status_code=500
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GoHighLevel Webhook Handler",
        "version": "1.0.0",
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
    logger.info(f"Webhook endpoint: http://localhost:{port}/webhook")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )