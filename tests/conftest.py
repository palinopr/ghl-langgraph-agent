"""
Pytest configuration and shared fixtures
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import pytz


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock application settings"""
    with patch('src.config.get_settings') as mock:
        settings = Mock()
        settings.openai_api_key = "test-key"
        settings.openai_model = "gpt-4o-mini"
        settings.supabase_url = "http://test.supabase.co"
        settings.supabase_anon_key = "test-anon-key"
        settings.ghl_api_token = "test-ghl-token"
        settings.ghl_location_id = "test-location"
        settings.ghl_calendar_id = "test-calendar"
        settings.ghl_assigned_user_id = "test-user"
        settings.ghl_api_base_url = "https://api.gohighlevel.com/v2"
        settings.webhook_secret = "test-secret"
        settings.port = 8000
        settings.debug = True
        mock.return_value = settings
        yield settings


@pytest.fixture
def sample_contact():
    """Sample contact data"""
    return {
        "id": "test-contact-123",
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "customFields": [
            {"id": "field1", "value": "value1"},
            {"id": "field2", "value": "value2"}
        ],
        "tags": ["new-lead", "interested"]
    }


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data from GoHighLevel"""
    return {
        "messageId": "msg-123",
        "contactId": "test-contact-123",
        "locationId": "test-location",
        "conversationId": "conv-123",
        "body": "I'm interested in your services",
        "type": "WhatsApp",
        "direction": "inbound",
        "contactName": "John Doe",
        "contactPhone": "+1234567890",
        "contactEmail": "john@example.com",
        "customFields": [
            {"id": "field1", "value": "value1"}
        ],
        "dateAdded": datetime.now(pytz.UTC).isoformat()
    }


@pytest.fixture
def sample_conversation_state():
    """Sample conversation state"""
    from langchain_core.messages import HumanMessage
    
    return {
        "messages": [HumanMessage(content="Hello, I need help")],
        "contact_id": "test-contact-123",
        "contact_info": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890"
        },
        "current_agent": None,
        "agent_responses": [],
        "conversation_history": []
    }


@pytest.fixture
def mock_ghl_client():
    """Mock GoHighLevel client"""
    with patch('src.tools.ghl_client.GHLClient') as mock_class:
        client = Mock()
        
        # Mock methods
        client.get_contact_details = AsyncMock(return_value={
            "id": "test-contact-123",
            "name": "John Doe",
            "email": "john@example.com"
        })
        
        client.send_message = AsyncMock(return_value={
            "messageId": "msg-sent-123",
            "status": "sent"
        })
        
        client.check_calendar_availability = AsyncMock(return_value=[
            {
                "start": "2024-01-15T10:00:00",
                "end": "2024-01-15T11:00:00"
            },
            {
                "start": "2024-01-15T14:00:00",
                "end": "2024-01-15T15:00:00"
            }
        ])
        
        client.create_appointment = AsyncMock(return_value={
            "id": "apt-123",
            "status": "confirmed"
        })
        
        mock_class.return_value = client
        yield client


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    with patch('src.tools.supabase_client.SupabaseClient') as mock_class:
        client = Mock()
        
        # Mock methods
        client.add_to_message_queue = AsyncMock(return_value={
            "id": "queue-123",
            "status": "pending"
        })
        
        client.get_pending_messages = AsyncMock(return_value=[])
        
        client.update_message_status = AsyncMock(return_value=True)
        
        client.add_to_responder_queue = AsyncMock(return_value={
            "id": "resp-123",
            "status": "pending"
        })
        
        mock_class.return_value = client
        yield client


@pytest.fixture
def mock_openai():
    """Mock OpenAI ChatOpenAI"""
    with patch('langchain_openai.ChatOpenAI') as mock_class:
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock()
        mock_class.return_value = mock_llm
        yield mock_llm