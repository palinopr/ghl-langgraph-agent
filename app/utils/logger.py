"""
Logging configuration for GoHighLevel LangGraph Agent
"""
import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, "contact_id"):
            log_data["contact_id"] = record.contact_id
        if hasattr(record, "agent"):
            log_data["agent"] = record.agent
        if hasattr(record, "score"):
            log_data["score"] = record.score
        if hasattr(record, "error"):
            log_data["error"] = str(record.error)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def setup_logging(
    name: Optional[str] = None,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        name: Logger name (defaults to root logger)
        level: Log level (defaults to settings.log_level)
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    try:
        settings = get_settings()
    except Exception:
        # If settings can't be loaded, use defaults
        class DefaultSettings:
            log_level = "INFO"
            app_env = "development"
        settings = DefaultSettings()
    
    # Get logger
    logger = logging.getLogger(name)
    
    # Set level
    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with human-readable format for development
    if settings.app_env == "development":
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    else:
        # JSON format for production
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return setup_logging(name)


# Convenience loggers for specific components
def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get a logger for an agent"""
    return get_logger(f"agent.{agent_name}")


def get_tool_logger(tool_name: str) -> logging.Logger:
    """Get a logger for a tool"""
    return get_logger(f"tool.{tool_name}")


def get_api_logger() -> logging.Logger:
    """Get a logger for API endpoints"""
    return get_logger("api")


def get_workflow_logger() -> logging.Logger:
    """Get a logger for workflow operations"""
    return get_logger("workflow")


# Utility functions for structured logging
def log_lead_analysis(logger: logging.Logger, contact_id: str, score: int, 
                     route: str, intent: str, **kwargs):
    """Log lead analysis results"""
    extra = {
        "contact_id": contact_id,
        "score": score,
        "route": route,
        "intent": intent
    }
    extra.update(kwargs)
    
    logger.info(
        f"Lead analysis complete - Score: {score}, Route: {route}, Intent: {intent}",
        extra=extra
    )


def log_agent_response(logger: logging.Logger, agent: str, contact_id: str, 
                      response: str, **kwargs):
    """Log agent response generation"""
    extra = {
        "agent": agent,
        "contact_id": contact_id,
        "response_preview": response[:100] + "..." if len(response) > 100 else response
    }
    extra.update(kwargs)
    
    logger.info(
        f"Agent {agent} generated response for {contact_id}",
        extra=extra
    )


def log_api_request(logger: logging.Logger, method: str, endpoint: str, 
                   status_code: Optional[int] = None, **kwargs):
    """Log API request details"""
    extra = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code
    }
    extra.update(kwargs)
    
    if status_code and status_code >= 400:
        logger.error(
            f"API request failed - {method} {endpoint}: {status_code}",
            extra=extra
        )
    else:
        logger.info(
            f"API request - {method} {endpoint}: {status_code or 'pending'}",
            extra=extra
        )


def log_error(logger: logging.Logger, error: Exception, context: str, **kwargs):
    """Log error with context"""
    extra = {
        "error": str(error),
        "error_type": type(error).__name__,
        "context": context
    }
    extra.update(kwargs)
    
    logger.error(
        f"Error in {context}: {str(error)}",
        exc_info=True,
        extra=extra
    )