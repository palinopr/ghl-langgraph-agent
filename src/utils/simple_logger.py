"""
Simple logger setup using structlog for structured logging
"""
import structlog


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger for consistent logging across the application"""
    return structlog.get_logger(name)