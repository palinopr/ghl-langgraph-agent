#!/usr/bin/env python3
"""
Set up a local server that mimics production environment with real GHL data
"""
import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from app.workflow import workflow as workflow_app
from app.tools.ghl_client import GHLClient
from app.tools.webhook_enricher import WebhookEnricher
from app.tools.conversation_loader import ConversationLoader
from app.state.conversation_state import ConversationState
from langchain_core.messages import HumanMessage, AIMessage
from app.utils.simple_logger import get_logger

logger = get_logger("local_ghl_test")

# Create FastAPI app
app = FastAPI(title="Local GHL Testing Environment")

# Initialize GHL clients
ghl_client = GHLClient()
webhook_enricher = WebhookEnricher()
conversation_loader = ConversationLoader()

@app.post("/webhook/test")
async def test_webhook(request: Request):
    """
    Receive test webhooks that mimic GHL exactly
    This endpoint processes messages just like production
    """
    try:
        # Get webhook data
        webhook_data = await request.json()
        logger.info(f"Received test webhook: {json.dumps(webhook_data, indent=2)}")
        
        # Enrich webhook with full GHL context (just like production!)
        enriched_data = await webhook_enricher.enrich_webhook(webhook_data)
        
        # Load conversation history from GHL
        messages = await conversation_loader.load_conversation(
            contact_id=webhook_data.get("contactId"),
            location_id=webhook_data.get("locationId")
        )
        
        # Create state exactly like production
        state = {
            "messages": messages,
            "contact_id": webhook_data.get("contactId"),
            "webhook_data": webhook_data,
            "contact_info": enriched_data.get("contact_info", {}),
            "previous_custom_fields": enriched_data.get("custom_fields", {}),
            "conversation_history": enriched_data.get("conversation_history", [])
        }
        
        # Run workflow (exact same as production)
        logger.info("Running workflow...")
        result = await workflow_app.ainvoke(state)
        
        # Extract response
        response_message = None
        if result.get("messages"):
            last_msg = result["messages"][-1]
            if isinstance(last_msg, AIMessage):
                response_message = last_msg.content
        
        # Log what would be sent to GHL
        logger.info(f"Response: {response_message}")
        
        # Return response
        return JSONResponse({
            "success": True,
            "response": response_message,
            "extracted_data": result.get("extracted_data"),
            "lead_score": result.get("lead_score"),
            "current_agent": result.get("current_agent"),
            "would_send_to_ghl": {
                "message": response_message,
                "contact_id": webhook_data.get("contactId"),
                "custom_fields": result.get("custom_fields_to_update", {})
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/webhook/ghl")
async def ghl_webhook_proxy(request: Request):
    """
    Receive actual GHL webhooks locally for testing
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received GHL webhook: {json.dumps(webhook_data, indent=2)}")
        
        # Process exactly like production
        return await test_webhook(request)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/test/{contact_id}/send")
async def send_test_message(contact_id: str, message: str):
    """
    Send a test message as if it came from a contact
    """
    # Create webhook data that mimics GHL
    webhook_data = {
        "id": f"test_{datetime.now().timestamp()}",
        "contactId": contact_id,
        "message": message,
        "body": message,
        "type": "SMS",
        "direction": "inbound",
        "dateAdded": datetime.now().isoformat(),
        "locationId": os.getenv("GHL_LOCATION_ID"),
        "assignedUserId": os.getenv("GHL_ASSIGNED_USER_ID"),
        "conversationId": f"conv_{contact_id}"
    }
    
    # Create a mock request
    class MockRequest:
        async def json(self):
            return webhook_data
    
    # Process it
    response = await test_webhook(MockRequest())
    return response

@app.get("/")
async def root():
    """
    Show available endpoints and instructions
    """
    return {
        "message": "Local GHL Testing Environment",
        "endpoints": {
            "/webhook/test": "POST - Send test webhooks",
            "/webhook/ghl": "POST - Receive actual GHL webhooks",
            "/test/{contact_id}/send?message=...": "GET - Quick test with contact",
            "/docs": "GET - API documentation"
        },
        "setup": {
            "1": "Set GHL webhook to: http://localhost:8001/webhook/ghl",
            "2": "Or use ngrok: ngrok http 8001",
            "3": "Then set GHL webhook to ngrok URL + /webhook/ghl"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Local GHL Testing Server")
    print("=" * 60)
    print("This server replicates the REAL production environment:")
    print("✅ Loads real contact data from GHL")
    print("✅ Loads real conversation history")
    print("✅ Uses actual webhook enrichment")
    print("✅ Processes with production workflow")
    print("=" * 60)
    print("\nOptions:")
    print("1. Test with curl:")
    print('   curl -X POST http://localhost:8001/webhook/test \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"contactId": "YOUR_CONTACT_ID", "message": "Hola"}\'')
    print("\n2. Use with ngrok for real GHL webhooks:")
    print("   ngrok http 8001")
    print("   Then update GHL webhook to: https://YOUR-NGROK.ngrok.io/webhook/ghl")
    print("\n3. Quick test:")
    print("   http://localhost:8001/test/YOUR_CONTACT_ID/send?message=Hola")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)