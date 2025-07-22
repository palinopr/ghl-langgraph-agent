"""
Observability configuration for OpenTelemetry

Provides auto-instrumentation for FastAPI and HTTPX with configurable OTLP exporter.
"""
import logging
import os
import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def configure_structured_logging() -> None:
    """Configure structlog for structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.dict_tracebacks,
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        handlers=[logging.StreamHandler()],
        level=logging.INFO,
    )
    logging.getLogger().handlers[0].setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer() if os.getenv("APP_ENV") == "development" else structlog.processors.JSONRenderer(),
        )
    )


def configure(app: FastAPI, service_name: str | None = None) -> None:
    """
    Configure OpenTelemetry instrumentation for the FastAPI application.

    Args:
        app: FastAPI application instance
        service_name: Optional service name (defaults to app title)
    """
    # Skip if already configured (important for tests)
    if hasattr(app.state, "_observability_configured"):
        return

    # Configure structured logging first
    configure_structured_logging()

    # Get configuration from environment
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name = service_name or app.title or "ghl-langgraph-agent"
    environment = os.getenv("APP_ENV", "development")

    # Mark as configured
    app.state._observability_configured = True

    # Create resource with service info
    resource = Resource.create({
        "service.name": service_name,
        "service.version": getattr(app, "version", "unknown"),
        "deployment.environment": environment,
    })

    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Configure span exporters
    if otlp_endpoint:
        # OTLP exporter for production
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=environment == "development",
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
        logger = structlog.get_logger()
        logger.info(
            "OpenTelemetry OTLP exporter configured",
            endpoint=otlp_endpoint,
            service_name=service_name,
            environment=environment
        )
    else:
        # Console exporter for development
        if environment == "development":
            tracer_provider.add_span_processor(
                BatchSpanProcessor(ConsoleSpanExporter())
            )
        logger = structlog.get_logger()
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT not configured",
            message="Traces will be exported to console in development mode only",
            environment=environment
        )

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument HTTPX for outgoing HTTP requests
    HTTPXClientInstrumentor().instrument()

    # Instrument logging to capture logs in traces
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Add middleware to inject trace context into request state
    # Check if app has been started (important for tests)
    if app.middleware_stack is None:
        @app.middleware("http")
        async def inject_trace_context(request, call_next):  # type: ignore
            """Inject current trace context into request state."""
            span = trace.get_current_span()
            if span and span.is_recording():
                trace_id = format(span.get_span_context().trace_id, '032x')
                request.state.trace_id = trace_id
                request.state.span_id = format(span.get_span_context().span_id, '016x')

            response = await call_next(request)

            # Add traceparent header to response for distributed tracing
            if span and span.is_recording():
                traceparent = f"00-{format(span.get_span_context().trace_id, '032x')}-{format(span.get_span_context().span_id, '016x')}-01"
                response.headers["traceparent"] = traceparent

            return response

    logger = structlog.get_logger()
    logger.info(
        "OpenTelemetry instrumentation configured",
        service_name=service_name,
        environment=environment,
        instrumented=["FastAPI", "HTTPX", "Logging"]
    )


# Export main function
__all__ = ["configure", "configure_structured_logging"]
