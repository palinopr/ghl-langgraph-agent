#!/usr/bin/env python3
"""
Development Server with Detailed Logging
- Shows exactly what's happening at each step
- Logs all state changes
- Tracks message flow through agents
- Easy to copy/paste logs
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Set up detailed logging
os.environ['LOG_LEVEL'] = 'DEBUG'
os.environ['LANGSMITH_TRACING'] = 'true'

from app.workflow import workflow
from app.utils.simple_logger import get_logger

# Create logger
logger = get_logger("dev_server")

# Create FastAPI app
app = FastAPI(title="LangGraph Dev Server", version="1.0.0")

# Store logs for easy retrieval
request_logs = []

class DetailedLogger:
    """Capture detailed logs for each request"""
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.logs = []
        self.start_time = datetime.now()
    
    def log(self, level: str, message: str, data: Any = None):
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "data": data
        }
        self.logs.append(log_entry)
        
        # Also print to console with color
        color_map = {
            "INFO": "\033[94m",    # Blue
            "SUCCESS": "\033[92m", # Green
            "WARNING": "\033[93m", # Yellow
            "ERROR": "\033[91m",   # Red
            "DEBUG": "\033[90m"    # Gray
        }
        color = color_map.get(level, "")
        reset = "\033[0m"
        
        print(f"{color}[{timestamp}] {level}: {message}{reset}")
        if data:
            print(f"{color}  Data: {json.dumps(data, indent=2)}{reset}")
    
    def get_summary(self):
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            "request_id": self.request_id,
            "duration_seconds": duration,
            "total_logs": len(self.logs),
            "logs": self.logs
        }

@app.get("/")
async def root():
    """Health check and info"""
    return {
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "/webhook": "POST - Send message through workflow",
            "/logs": "GET - Get all request logs",
            "/logs/{request_id}": "GET - Get specific request logs"
        }
    }

@app.post("/webhook")
async def process_webhook(request: Request):
    """Process webhook with detailed logging"""
    request_id = f"req_{int(datetime.now().timestamp())}"
    req_logger = DetailedLogger(request_id)
    
    try:
        # Get request body
        body = await request.json()
        req_logger.log("INFO", "Received webhook request", body)
        
        # Extract key fields
        contact_id = body.get("contactId", body.get("id", "unknown"))
        message = body.get("message", body.get("body", ""))
        
        req_logger.log("INFO", f"Processing message from contact: {contact_id}", {
            "contact_id": contact_id,
            "message": message
        })
        
        # Create webhook data
        webhook_data = {
            "id": body.get("id", f"msg_{int(datetime.now().timestamp())}"),
            "contactId": contact_id,
            "conversationId": body.get("conversationId", f"conv_{contact_id}"),
            "message": message,
            "body": message,
            "type": body.get("type", "SMS"),
            "locationId": body.get("locationId", os.getenv("GHL_LOCATION_ID")),
            "direction": "inbound",
            "dateAdded": body.get("dateAdded", datetime.now().isoformat())
        }
        
        # Create initial state
        initial_state = {
            "webhook_data": webhook_data,
            "contact_id": contact_id,
            "contact_info": {},
            "conversation_history": [],
            "previous_custom_fields": {},
            "messages": []
        }
        
        req_logger.log("INFO", "Created initial state", {
            "contact_id": contact_id,
            "webhook_keys": list(webhook_data.keys())
        })
        
        # Configure workflow
        config = {
            "configurable": {
                "thread_id": f"dev-{contact_id}-{request_id}",
                "checkpoint_ns": ""
            },
            "metadata": {
                "source": "dev_server",
                "request_id": request_id
            }
        }
        
        req_logger.log("INFO", "Starting workflow execution...")
        
        # Track workflow steps
        step_count = 0
        
        # Custom callback to log steps
        async def log_step(step_data):
            nonlocal step_count
            step_count += 1
            req_logger.log("DEBUG", f"Step {step_count}: {step_data.get('node', 'unknown')}", step_data)
        
        # Run workflow
        try:
            result = await workflow.ainvoke(initial_state, config)
            
            req_logger.log("SUCCESS", "Workflow completed successfully")
            
            # Extract key results
            final_state_summary = {
                "lead_score": result.get("lead_score", "N/A"),
                "current_agent": result.get("current_agent", "N/A"),
                "next_agent": result.get("next_agent", "N/A"),
                "appointment_status": result.get("appointment_status", "N/A"),
                "messages_count": len(result.get("messages", [])),
                "extracted_data": result.get("extracted_data", {})
            }
            
            req_logger.log("INFO", "Final state summary", final_state_summary)
            
            # Find AI response
            ai_response = None
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                    ai_response = msg.content
                    break
            
            if ai_response:
                req_logger.log("SUCCESS", f"AI Response: {ai_response[:200]}...")
            
            # Store logs
            log_summary = req_logger.get_summary()
            request_logs.append(log_summary)
            
            # Keep only last 100 requests
            if len(request_logs) > 100:
                request_logs.pop(0)
            
            return JSONResponse({
                "success": True,
                "request_id": request_id,
                "contact_id": contact_id,
                "ai_response": ai_response,
                "final_state": final_state_summary,
                "log_url": f"/logs/{request_id}"
            })
            
        except Exception as e:
            req_logger.log("ERROR", f"Workflow failed: {str(e)}")
            log_summary = req_logger.get_summary()
            request_logs.append(log_summary)
            
            return JSONResponse({
                "success": False,
                "request_id": request_id,
                "error": str(e),
                "log_url": f"/logs/{request_id}"
            }, status_code=500)
            
    except Exception as e:
        req_logger.log("ERROR", f"Request processing failed: {str(e)}")
        log_summary = req_logger.get_summary()
        request_logs.append(log_summary)
        
        return JSONResponse({
            "success": False,
            "request_id": request_id,
            "error": str(e),
            "log_url": f"/logs/{request_id}"
        }, status_code=400)

@app.get("/logs")
async def get_all_logs():
    """Get all request logs"""
    return {
        "total_requests": len(request_logs),
        "requests": [
            {
                "request_id": log["request_id"],
                "duration": log["duration_seconds"],
                "total_logs": log["total_logs"],
                "url": f"/logs/{log['request_id']}"
            }
            for log in request_logs
        ]
    }

@app.get("/logs/{request_id}")
async def get_request_logs(request_id: str):
    """Get logs for specific request"""
    for log in request_logs:
        if log["request_id"] == request_id:
            return log
    
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/test")
async def test_message():
    """Quick test endpoint"""
    test_data = {
        "contactId": "test123",
        "message": "Hola",
        "type": "SMS",
        "locationId": os.getenv("GHL_LOCATION_ID", "test")
    }
    
    return await process_webhook(Request(
        scope={
            "type": "http",
            "method": "POST",
            "headers": [],
            "query_string": b""
        },
        receive=lambda: {"type": "http.request", "body": json.dumps(test_data).encode()},
        send=lambda x: None
    ))

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 LANGGRAPH DEV SERVER")
    print("="*60)
    print("Endpoints:")
    print("  POST http://localhost:8001/webhook - Process message")
    print("  GET  http://localhost:8001/logs - View all logs")
    print("  GET  http://localhost:8001/logs/{id} - View specific request")
    print("  POST http://localhost:8001/test - Quick test")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)