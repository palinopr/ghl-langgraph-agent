"""
Webhook proxy that properly manages LangGraph Cloud threads
Uses the LangGraph SDK to maintain conversation continuity
"""
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from langgraph_sdk import get_client
import os
import json
from datetime import datetime
import logging
import redis
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
LANGGRAPH_API_URL = os.getenv(
    "LANGGRAPH_API_URL", 
    "https://ghl-langgraph-agent-95f8713b0bd6545391589bd2f0ca67eb.us.langgraph.app"
)
LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "agent")

# Thread mapping storage (use Redis in production)
thread_map: Dict[str, str] = {}

# Initialize Redis client if available
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    USE_REDIS = True
    logger.info("Connected to Redis for thread mapping")
except:
    redis_client = None
    USE_REDIS = False
    logger.warning("Redis not available, using in-memory thread mapping")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LangGraph client on startup"""
    global langgraph_client
    langgraph_client = get_client(
        url=LANGGRAPH_API_URL,
        api_key=LANGGRAPH_API_KEY
    )
    logger.info(f"Connected to LangGraph Cloud: {LANGGRAPH_API_URL}")
    yield
    # Cleanup
    logger.info("Shutting down webhook proxy")


app = FastAPI(
    title="GHL-LangGraph Webhook Proxy",
    description="Manages thread continuity for LangGraph Cloud",
    version="2.0.0",
    lifespan=lifespan
)


async def get_or_create_thread(conversation_id: str, contact_id: str) -> str:
    """Get existing thread or create new one for conversation"""
    
    # Generate our preferred thread key
    thread_key = f"conv-{conversation_id}" if conversation_id else f"contact-{contact_id}"
    
    # Check thread mapping
    if USE_REDIS:
        existing_thread = redis_client.get(f"thread:{thread_key}")
    else:
        existing_thread = thread_map.get(thread_key)
    
    if existing_thread:
        logger.info(f"Using existing thread {existing_thread} for {thread_key}")
        return existing_thread
    
    # Create new thread
    try:
        thread_response = await langgraph_client.threads.create()
        thread_id = thread_response["thread_id"]
        
        # Store mapping
        if USE_REDIS:
            redis_client.set(f"thread:{thread_key}", thread_id, ex=86400*7)  # 7 days TTL
        else:
            thread_map[thread_key] = thread_id
        
        logger.info(f"Created new thread {thread_id} for {thread_key}")
        return thread_id
        
    except Exception as e:
        logger.error(f"Error creating thread: {e}")
        # Fallback to using our key as thread_id
        return thread_key


@app.post("/webhook/message")
async def handle_ghl_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive webhook from GoHighLevel and invoke LangGraph with proper thread management
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received webhook: {json.dumps(webhook_data, indent=2)}")
        
        # Extract identifiers
        contact_id = webhook_data.get("contactId", webhook_data.get("id", "unknown"))
        conversation_id = webhook_data.get("conversationId")
        message_body = webhook_data.get("body", webhook_data.get("message", ""))
        
        if not contact_id:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing contact ID"}
            )
        
        # Get or create thread
        thread_id = await get_or_create_thread(conversation_id, contact_id)
        
        # Add task to process in background
        background_tasks.add_task(
            invoke_langgraph_with_thread,
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
                "thread_key": f"conv-{conversation_id}" if conversation_id else f"contact-{contact_id}",
                "message": "Webhook received and processing"
            }
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def invoke_langgraph_with_thread(
    webhook_data: Dict[str, Any],
    thread_id: str,
    contact_id: str,
    conversation_id: Optional[str],
    message_body: str
):
    """
    Invoke LangGraph Cloud using SDK with proper thread management
    """
    try:
        # Prepare input for workflow
        workflow_input = {
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "thread_id": thread_id,  # This will be processed by thread_mapper
            "conversation_id": conversation_id,
            "messages": [],  # Will be populated by receptionist
            "lead_score": 0,
            "extracted_data": {},
            "is_new_conversation": False,  # We're managing threads
            "conversation_stage": "ongoing",
            "location_id": webhook_data.get("locationId", ""),
            "should_end": False,
            "needs_escalation": False,
            "supervisor_complete": False,
            "message_sent": False
        }
        
        logger.info(f"Invoking LangGraph for thread {thread_id}")
        logger.info(f"Message: {message_body}")
        
        # Use SDK to run with specific thread
        run = await langgraph_client.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            input=workflow_input
        )
        
        logger.info(f"✅ LangGraph run created: {run['run_id']}")
        logger.info(f"Thread ID confirmed: {run['thread_id']}")
        
        # Wait for completion (with timeout)
        final_state = await langgraph_client.runs.wait(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID, 
            run_id=run['run_id'],
            timeout=30
        )
        
        if final_state:
            logger.info(f"✅ Run completed successfully")
            logger.info(f"Final status: {final_state.get('status')}")
        else:
            logger.warning(f"Run timed out or failed to complete")
                
    except Exception as e:
        logger.error(f"Error invoking LangGraph: {e}", exc_info=True)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    thread_count = len(thread_map) if not USE_REDIS else -1
    
    return {
        "status": "healthy",
        "service": "webhook-proxy-sdk",
        "langgraph_url": LANGGRAPH_API_URL,
        "assistant_id": ASSISTANT_ID,
        "api_key_configured": bool(LANGGRAPH_API_KEY),
        "storage": "redis" if USE_REDIS else "memory",
        "thread_mappings": thread_count,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/threads/{conversation_id}")
async def get_thread_info(conversation_id: str):
    """Get thread information for a conversation"""
    thread_key = f"conv-{conversation_id}"
    
    if USE_REDIS:
        thread_id = redis_client.get(f"thread:{thread_key}")
    else:
        thread_id = thread_map.get(thread_key)
    
    if not thread_id:
        return JSONResponse(
            status_code=404,
            content={"error": "Thread not found for conversation"}
        )
    
    return {
        "conversation_id": conversation_id,
        "thread_key": thread_key,
        "thread_id": thread_id,
        "exists": True
    }


@app.delete("/threads/{conversation_id}")
async def reset_thread(conversation_id: str):
    """Reset thread mapping for a conversation"""
    thread_key = f"conv-{conversation_id}"
    
    if USE_REDIS:
        redis_client.delete(f"thread:{thread_key}")
    else:
        thread_map.pop(thread_key, None)
    
    return {
        "status": "success",
        "message": f"Thread mapping reset for {conversation_id}"
    }


@app.get("/")
async def root():
    """Root endpoint with instructions"""
    return {
        "service": "GHL-LangGraph Webhook Proxy",
        "version": "2.0.0",
        "purpose": "Manages thread continuity for LangGraph Cloud using SDK",
        "endpoints": {
            "/webhook/message": "POST - Receive GHL webhooks",
            "/health": "GET - Health check",
            "/threads/{conversation_id}": "GET - Get thread info",
            "/threads/{conversation_id}": "DELETE - Reset thread mapping"
        },
        "benefits": [
            "Maintains conversation continuity",
            "Uses LangGraph SDK for proper thread management",
            "Stores conversation→thread mappings",
            "Supports Redis for production scalability"
        ]
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )