"""
Main entry point for the GoHighLevel LangGraph Agent
"""
import os
import uvicorn
from app.api.webhook import app

if __name__ == "__main__":
    # Get port from environment with default
    port = int(os.environ.get("PORT", 8000))
    
    print(f"Starting server on 0.0.0.0:{port}")
    
    # Run the FastAPI application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )