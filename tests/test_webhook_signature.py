"""
Integration tests for webhook signature verification in FastAPI
"""
import json
import os
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from src.security import generate_signature


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    with patch.dict(os.environ, {"GHL_WEBHOOK_SECRET": "test-secret-key"}):
        yield


@pytest.fixture
def mock_workflow():
    """Mock the workflow processing"""
    with patch("app.api.webhook_simple.run_workflow", new_callable=AsyncMock) as mock:
        mock.return_value = {"success": True}
        yield mock


@pytest.fixture
def client(mock_workflow):
    """Create test client"""
    from app.api.webhook_simple import app
    return TestClient(app)


class TestWebhookSignatureEndpoint:
    """Test webhook signature verification in FastAPI endpoint"""
    
    def test_valid_signature_accepted(self, client, mock_env):
        """Test that valid signatures are accepted"""
        body = {"contactId": "123", "message": "Hello"}
        # Use json.dumps without spaces after separators to match FastAPI's serialization
        body_json = json.dumps(body, separators=(',', ':'))
        
        # Generate valid signature
        signature = generate_signature(body_json, "test-secret-key")
        
        response = client.post(
            "/webhook/ghl",
            content=body_json,
            headers={
                "X-GHL-Signature": signature,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["signature_verified"] is True
        
    def test_invalid_signature_rejected(self, client, mock_env):
        """Test that invalid signatures are rejected"""
        body = {"contactId": "123", "message": "Hello"}
        body_json = json.dumps(body, separators=(',', ':'))
        
        # Generate signature with wrong secret
        signature = generate_signature(body_json, "wrong-secret")
        
        response = client.post(
            "/webhook/ghl",
            content=body_json,
            headers={
                "X-GHL-Signature": signature,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "INVALID_SIGNATURE"
        
    def test_missing_signature_rejected(self, client, mock_env):
        """Test that missing signatures are rejected when secret is configured"""
        body = {"contactId": "123", "message": "Hello"}
        
        response = client.post("/webhook/ghl", json=body)
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "INVALID_SIGNATURE"
        assert "Missing signature header" in data["message"]
        
    def test_no_secret_allows_unsigned(self, client, mock_workflow):
        """Test that webhooks work without signature when secret not configured"""
        # Don't mock environment, so GHL_WEBHOOK_SECRET is not set
        body = {"contactId": "123", "message": "Hello"}
        
        response = client.post("/webhook/ghl", json=body)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["signature_verified"] is False
        
    def test_missing_contact_id_rejected(self, client):
        """Test that webhooks without contact ID are rejected"""
        body = {"message": "Hello"}  # No contactId
        
        response = client.post("/webhook/ghl", json=body)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Missing contact ID"
        
    def test_malformed_signature_header(self, client, mock_env):
        """Test that malformed signature headers are rejected"""
        body = {"contactId": "123", "message": "Hello"}
        
        response = client.post(
            "/webhook/ghl",
            json=body,
            headers={"X-GHL-Signature": "invalid-format"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "INVALID_SIGNATURE"