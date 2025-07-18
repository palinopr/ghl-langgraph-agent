"""Minimal FastAPI app for testing deployment"""
from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def root():
    return {
        "status": "healthy",
        "message": "Test deployment successful",
        "port": os.environ.get("PORT", "unknown")
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# For gunicorn
application = app