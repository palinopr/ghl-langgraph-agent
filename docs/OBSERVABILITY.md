# Observability Configuration

## Overview

This application uses OpenTelemetry for distributed tracing and structured logging with `structlog` for enhanced debugging capabilities. All HTTP requests, workflow executions, and agent interactions are automatically instrumented.

## Configuration

### Environment Variables

```bash
# Required for remote tracing (optional for local development)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Application environment
APP_ENV=development  # or production
```

### Auto-Instrumentation

The following components are automatically instrumented:
- **FastAPI**: All HTTP endpoints with request/response details
- **HTTPX**: Outgoing HTTP requests to external services
- **Logging**: Log messages are correlated with trace spans

## Trace Context

Every request includes trace context in:
- Request state: `request.state.trace_id` and `request.state.span_id`
- Response headers: `traceparent` header for distributed tracing
- Log messages: Automatically included in structured logs

## Structured Logging

All log messages use structured format with contextual fields:

```python
logger.info("Webhook received", 
    contact_id=contact_id,
    conversation_id=conversation_id,
    thread_id=thread_id
)
```

## Local Development

Without OTLP endpoint configured, traces are exported to console in development mode. To see traces:

1. Run the application
2. Make requests
3. Check console output for span details

## Production Setup

For production, configure OTLP endpoint to send traces to your observability platform (Jaeger, Tempo, etc.):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector:4317
APP_ENV=production
```

## Debugging Context Loss

To debug conversation context issues:

1. Check trace for `thread_id` consistency across requests
2. Look for checkpoint loading logs with structured fields
3. Verify `conversation_id` mapping in traces
4. Monitor span errors for checkpoint failures