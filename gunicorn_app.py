"""Gunicorn application entry point"""
from src.api.webhook import app

# Export the FastAPI app for Gunicorn
application = app