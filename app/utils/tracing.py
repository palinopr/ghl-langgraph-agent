"""
LangSmith tracing configuration for monitoring and debugging
"""
import os
import time
import functools
from typing import Dict, Any, Optional, TypeVar, Callable
from langsmith import Client
from langchain_core.tracers.context import tracing_v2_enabled
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("tracing")

T = TypeVar('T')


def setup_langsmith_tracing():
    """
    Configure LangSmith tracing for all LangChain/LangGraph operations
    
    This should be called once at application startup
    """
    settings = get_settings()
    
    # Set environment variables for LangSmith
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    
    if not langsmith_api_key:
        logger.warning("LangSmith API key not found. Tracing will be disabled.")
        return False
    
    # Configure LangSmith environment
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent")
    
    # Legacy support
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent")
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    logger.info(f"LangSmith tracing enabled for project: {os.environ['LANGSMITH_PROJECT']}")
    
    try:
        # Verify connection
        client = Client()
        # Test the connection
        client.list_projects(limit=1)
        logger.info("LangSmith connection verified successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to LangSmith: {e}")
        return False


def get_tracing_metadata(
    contact_id: str,
    agent_name: Optional[str] = None,
    workflow_run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get metadata for tracing context
    
    Args:
        contact_id: Contact ID for the conversation
        agent_name: Current agent handling the request
        workflow_run_id: Unique workflow run identifier
        
    Returns:
        Metadata dictionary for tracing
    """
    metadata = {
        "contact_id": contact_id,
        "environment": os.getenv("APP_ENV", "production"),
        "service": "ghl-langgraph-agent",
    }
    
    if agent_name:
        metadata["agent"] = agent_name
        
    if workflow_run_id:
        metadata["workflow_run_id"] = workflow_run_id
        
    return metadata


def trace_operation(
    operation_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None
):
    """
    Decorator/Context manager for tracing specific operations
    
    Usage as decorator:
        @trace_operation("state.read")
        async def my_function():
            pass
            
    Usage as context manager:
        async with trace_operation("intelligence_analysis", metadata={"contact_id": "123"}):
            # Your operation here
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            metadata_with_timing = {
                **(metadata or {}),
                "function": func.__name__,
                "start_time": start_time
            }
            
            async with TracedOperation(operation_name, metadata=metadata_with_timing, tags=tags or []):
                try:
                    result = await func(*args, **kwargs)
                    # Log success metrics
                    duration = time.time() - start_time
                    logger.debug(f"{operation_name} completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    # Log error metrics
                    duration = time.time() - start_time
                    logger.error(f"{operation_name} failed after {duration:.3f}s: {str(e)}")
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            metadata_with_timing = {
                **(metadata or {}),
                "function": func.__name__,
                "start_time": start_time
            }
            
            with trace_operation_context(operation_name, metadata=metadata_with_timing, tags=tags or []):
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.debug(f"{operation_name} completed in {duration:.3f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"{operation_name} failed after {duration:.3f}s: {str(e)}")
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    # If called with arguments, return decorator
    # If called as function, check if first arg is callable
    if operation_name and callable(operation_name):
        # Called as @trace_operation without parentheses
        func = operation_name
        operation_name = func.__name__
        return decorator(func)
    
    # Called with parentheses, return decorator
    return decorator


def trace_operation_context(
    operation_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None
):
    """
    Context manager version of trace_operation
    """
    if metadata is None:
        metadata = {}
        
    if tags is None:
        tags = []
    
    # Add default tags
    tags.extend(["ghl-agent", os.getenv("APP_ENV", "production")])
    
    # tracing_v2_enabled doesn't support metadata parameter
    # We'll store metadata in tags as a workaround
    if metadata:
        for key, value in metadata.items():
            tags.append(f"{key}:{value}")
    
    return tracing_v2_enabled(
        project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
        tags=tags
    )


class TracedOperation:
    """
    Helper class for adding tracing to async operations
    """
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.metadata = kwargs.get("metadata", {})
        self.tags = kwargs.get("tags", [])
        
    async def __aenter__(self):
        self.context = trace_operation(self.name, self.metadata, self.tags)
        # tracing_v2_enabled returns a synchronous context manager
        self.context.__enter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.context.__exit__(exc_type, exc_val, exc_tb)


# Singleton client instance
_langsmith_client = None


def get_langsmith_client() -> Optional[Client]:
    """Get or create LangSmith client instance"""
    global _langsmith_client
    
    if _langsmith_client is None:
        try:
            _langsmith_client = Client()
        except Exception as e:
            logger.error(f"Failed to create LangSmith client: {e}")
            return None
            
    return _langsmith_client


def log_feedback(
    run_id: str,
    score: float,
    feedback_type: str = "lead_quality",
    comment: Optional[str] = None
):
    """
    Log feedback to LangSmith for a specific run
    
    Args:
        run_id: The LangSmith run ID
        score: Score value (0-1 for quality, actual score for lead_score)
        feedback_type: Type of feedback (lead_quality, lead_score, agent_performance)
        comment: Optional comment
    """
    client = get_langsmith_client()
    if not client:
        return
        
    try:
        client.create_feedback(
            run_id=run_id,
            key=feedback_type,
            score=score,
            comment=comment
        )
        logger.debug(f"Logged feedback for run {run_id}: {feedback_type}={score}")
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")


# Auto-setup on import
_tracing_enabled = setup_langsmith_tracing()


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled"""
    return _tracing_enabled


__all__ = [
    "setup_langsmith_tracing",
    "get_tracing_metadata",
    "trace_operation",
    "TracedOperation",
    "get_langsmith_client",
    "log_feedback",
    "is_tracing_enabled"
]