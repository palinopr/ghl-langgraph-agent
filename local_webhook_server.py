#!/usr/bin/env python3
"""
Local Webhook Server for Testing LangGraph Agent
Works with the existing workflow without LangSmith dependency
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from langgraph_sdk import get_client

# Import your existing workflow
from app.workflow import workflow, ProductionState
from app.utils.simple_logger import get_logger
from app.utils.debug_helpers import log_state_transition, validate_state

logger = get_logger("local_webhook")

app = FastAPI(title="Local LangGraph Webhook Server")

# In-memory message storage for testing
message_history = {}


@app.get("/")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "local-langgraph-webhook"}


@app.post("/webhook/ghl")
async def ghl_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint that mimics GoHighLevel webhook
    Processes messages through the LangGraph workflow
    """
    try:
        # Parse webhook data
        webhook_data = await request.json()
        logger.info(f"Received webhook: {json.dumps(webhook_data, indent=2)}")
        
        # Extract key information
        contact_id = webhook_data.get("contactId", "")
        conversation_id = webhook_data.get("conversationId", "")
        message_body = webhook_data.get("body", "")
        
        if not contact_id or not message_body:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing contactId or message body"}
            )
        
        # Create thread ID
        thread_id = f"conv-{conversation_id}" if conversation_id else f"contact-{contact_id}"
        
        # Process in background
        background_tasks.add_task(
            process_message_locally,
            webhook_data=webhook_data,
            thread_id=thread_id,
            contact_id=contact_id,
            message_body=message_body
        )
        
        return JSONResponse(
            status_code=200,
            content={"status": "processing", "thread_id": thread_id}
        )
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def process_message_locally(
    webhook_data: Dict[str, Any],
    thread_id: str,
    contact_id: str,
    message_body: str
):
    """
    Process message through local workflow
    """
    logger.info(f"Processing message for thread: {thread_id}")
    
    try:
        # Create initial state
        initial_state = {
            "messages": [],  # Start empty, let receptionist load from mock
            "contact_id": contact_id,
            "conversation_id": webhook_data.get("conversationId", ""),
            "location_id": webhook_data.get("locationId", ""),
            "webhook_data": webhook_data,
            "thread_id": thread_id,
            "current_agent": "receptionist",
            "lead_score": 0
        }
        
        # Log initial state
        log_state_transition(initial_state, "webhook", "input")
        
        # Validate initial state
        validation = validate_state(initial_state, "webhook_initial")
        if not validation["valid"]:
            logger.warning(f"Initial state issues: {validation['issues']}")
        
        # Configure workflow execution
        config = {
            "configurable": {
                "thread_id": thread_id
            },
            "recursion_limit": 10
        }
        
        # Execute workflow
        logger.info("Executing workflow...")
        result = await workflow.ainvoke(initial_state, config)
        
        # Log result
        logger.info(f"Workflow completed. Final messages: {len(result.get('messages', []))}")
        
        # Store in memory for testing
        message_history[thread_id] = {
            "timestamp": datetime.now().isoformat(),
            "input": message_body,
            "result": result,
            "message_count": len(result.get('messages', []))
        }
        
        # Simulate sending to GHL (in real scenario, this would call GHL API)
        last_message = None
        messages = result.get('messages', [])
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                last_message = msg.content
                break
        
        if last_message:
            logger.info(f"Would send to GHL: {last_message[:100]}...")
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        message_history[thread_id] = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@app.get("/history/{thread_id}")
async def get_history(thread_id: str):
    """Get message history for a thread"""
    return message_history.get(thread_id, {"error": "Thread not found"})


@app.get("/history")
async def list_history():
    """List all threads"""
    return {
        "threads": list(message_history.keys()),
        "count": len(message_history)
    }


@app.post("/test")
async def test_message(contact_id: str, message: str):
    """
    Test endpoint to send a message without full webhook data
    """
    webhook_data = {
        "contactId": contact_id,
        "conversationId": f"test-conv-{datetime.now().timestamp()}",
        "body": message,
        "type": "InboundMessage",
        "locationId": "test-location"
    }
    
    return await ghl_webhook(
        Request(
            scope={
                "type": "http",
                "method": "POST",
                "headers": [],
                "query_string": b""
            },
            receive=lambda: {"body": json.dumps(webhook_data).encode()}
        ),
        BackgroundTasks()
    )


if __name__ == "__main__":
    import os
    
    # Disable LangSmith for local testing
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    
    print("🚀 Starting Local Webhook Server")
    print("📍 Webhook URL: http://localhost:8001/webhook/ghl")
    print("🧪 Test URL: http://localhost:8001/test")
    print("📊 History URL: http://localhost:8001/history")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )