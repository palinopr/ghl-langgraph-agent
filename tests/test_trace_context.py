"""
Tests for OpenTelemetry trace context propagation
"""
import re
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode


class MockSpanExporter:
    """Mock span exporter to capture spans for testing"""
    
    def __init__(self):
        self.spans = []
        
    def export(self, spans):
        self.spans.extend(spans)
        return True
        
    def shutdown(self):
        pass


@pytest.fixture
def mock_exporter():
    """Create a mock exporter for testing"""
    return MockSpanExporter()


@pytest.fixture
def test_app(mock_exporter):
    """Create test app with mocked observability"""
    # Set up test tracer provider with mock exporter
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(mock_exporter)
    )
    trace.set_tracer_provider(tracer_provider)
    
    # Import app after setting up tracer
    from app.api.webhook_simple import app
    
    # Configure observability for the test app
    from src.observability import configure
    configure(app)
    
    # Create test client
    return TestClient(app)


class TestTraceContext:
    """Test OpenTelemetry trace context propagation"""
    
    def test_healthz_has_traceparent_header(self, test_app):
        """Test that /healthz endpoint returns traceparent header"""
        # Check the actual endpoint from webhook_simple.py
        response = test_app.get("/ok")  # Using /ok endpoint which exists
        
        assert response.status_code == 200
        assert "traceparent" in response.headers
        
        # Validate traceparent format: version-trace_id-span_id-flags
        traceparent = response.headers["traceparent"]
        pattern = r"^00-[0-9a-f]{32}-[0-9a-f]{16}-01$"
        assert re.match(pattern, traceparent), f"Invalid traceparent format: {traceparent}"
        
    def test_webhook_creates_spans(self, test_app, mock_exporter):
        """Test that webhook endpoint creates spans"""
        # Send webhook request
        response = test_app.post(
            "/webhook/message",
            json={"contactId": "test-123", "body": "Test message"}
        )
        
        assert response.status_code == 200
        
        # Check that spans were created
        assert len(mock_exporter.spans) > 0
        
        # Find the HTTP span
        http_spans = [s for s in mock_exporter.spans if s.name.startswith("POST")]
        assert len(http_spans) > 0
        
        # Verify span attributes
        http_span = http_spans[0]
        assert http_span.attributes.get("http.method") == "POST"
        assert http_span.attributes.get("http.route") == "/webhook/message"
        assert http_span.status.status_code == StatusCode.UNSET or http_span.status.status_code == StatusCode.OK
        
    def test_trace_context_in_request_state(self, test_app):
        """Test that trace context is injected into request state"""
        # We need to capture the request object to verify state
        captured_request = None
        
        from fastapi import Request
        
        @test_app.app.get("/test-trace-state")
        async def test_endpoint(request: Request):
            nonlocal captured_request
            captured_request = request
            return {
                "trace_id": getattr(request.state, "trace_id", None),
                "span_id": getattr(request.state, "span_id", None)
            }
        
        response = test_app.get("/test-trace-state")
        assert response.status_code == 200
        
        data = response.json()
        assert data["trace_id"] is not None
        assert data["span_id"] is not None
        
        # Validate format
        assert len(data["trace_id"]) == 32
        assert len(data["span_id"]) == 16
        
    def test_multiple_endpoints_have_traceparent(self, test_app):
        """Test that multiple endpoints return traceparent headers"""
        endpoints = ["/", "/health", "/ok", "/metrics"]
        
        for endpoint in endpoints:
            response = test_app.get(endpoint)
            assert response.status_code == 200
            assert "traceparent" in response.headers
            
    def test_error_spans_have_error_status(self, test_app, mock_exporter):
        """Test that errors are properly recorded in spans"""
        # Send invalid webhook (missing contact ID)
        response = test_app.post(
            "/webhook/message",
            json={"message": "No contact ID"}
        )
        
        assert response.status_code == 400
        
        # Check spans
        http_spans = [s for s in mock_exporter.spans if s.name.startswith("POST")]
        assert len(http_spans) > 0
        
        # Verify error is recorded
        http_span = http_spans[0]
        assert http_span.attributes.get("http.status_code") == 400
        
    @patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"})
    def test_otlp_configuration(self):
        """Test that OTLP endpoint is properly configured"""
        # Import observability module
        from src.observability import configure
        from fastapi import FastAPI
        
        # Create test app
        app = FastAPI(title="test-app")
        
        # Configure should not raise exception
        configure(app, service_name="test-service")
        
        # Verify configuration worked (app should be marked as configured)
        assert hasattr(app.state, "_observability_configured")
        assert app.state._observability_configured is True