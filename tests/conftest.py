"""Pytest configuration and fixtures"""
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["GHL_API_TOKEN"] = "test-token"


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    from app.api.webhook_simple import app
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    from app.api.webhook_simple import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_webhook_payload() -> dict:
    """Sample GHL webhook payload for testing."""
    return {
        "contactId": "test-contact-123",
        "conversationId": "test-conversation-456",
        "locationId": "test-location-789",
        "message": "Hola, necesito información sobre sus servicios",
        "type": "WhatsApp",
        "direction": "inbound"
    }