"""
Main entry point for the GoHighLevel LangGraph Agent
"""
import uvicorn
from src.api.webhook import app
from src.config import get_settings
from src.utils.logger import setup_logging

# Set up logging
setup_logging()

# Get settings
settings = get_settings()


if __name__ == "__main__":
    # Run the FastAPI application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_level="info"
    )