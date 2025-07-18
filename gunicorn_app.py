"""Gunicorn application entry point"""
from app.api.webhook import app

# Export the FastAPI app for Gunicorn
application = app