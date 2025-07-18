"""
Error recovery utilities for LangGraph agents
Provides resilient error handling and graceful degradation
"""
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from functools import wraps
import asyncio
import time
from langgraph.errors import GraphRecursionError
from app.utils.simple_logger import get_logger

logger = get_logger("error_recovery")

T = TypeVar('T')


class RecoverableError(Exception):
    """Base class for errors that can be recovered from"""
    def __init__(self, message: str, recovery_action: Optional[str] = None):
        super().__init__(message)
        self.recovery_action = recovery_action


class APIError(RecoverableError):
    """Error from external API calls"""
    pass


class RateLimitError(RecoverableError):
    """Rate limit exceeded error"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, "wait_and_retry")
        self.retry_after = retry_after or 60


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    recoverable_errors: tuple = (APIError, RateLimitError, asyncio.TimeoutError)
):
    """
    Decorator for automatic retry with exponential backoff
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except recoverable_errors as e:
                    last_error = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Max retries ({max_attempts}) exceeded for {func.__name__}")
                        raise
                    
                    # Calculate delay
                    delay = initial_delay * (backoff_factor ** attempt)
                    
                    # Special handling for rate limits
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                    raise
            
            # Should never reach here, but just in case
            if last_error:
                raise last_error
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except recoverable_errors as e:
                    last_error = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(f"Max retries ({max_attempts}) exceeded for {func.__name__}")
                        raise
                    
                    delay = initial_delay * (backoff_factor ** attempt)
                    
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Non-recoverable error in {func.__name__}: {e}")
                    raise
            
            if last_error:
                raise last_error
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def handle_graph_recursion(max_depth: int = 25):
    """
    Decorator to handle graph recursion errors
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(state: Dict[str, Any], *args, **kwargs):
            try:
                return await func(state, *args, **kwargs)
            except GraphRecursionError as e:
                logger.error(f"Graph recursion limit hit: {e}")
                
                # Return a safe state that ends the conversation
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "I notice we've been going in circles. Let me summarize what we've discussed "
                                 "and provide you with the best next steps."
                    }],
                    "should_continue": False,
                    "error": "recursion_limit",
                    "recursion_depth": max_depth
                }
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for external services
    """
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def __call__(self, func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise APIError(
                        f"Circuit breaker is OPEN for {func.__name__}. "
                        f"Service unavailable, retry after {self.recovery_timeout}s"
                    )
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise APIError(f"Circuit breaker: {e}") from e
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise APIError(
                        f"Circuit breaker is OPEN. Service unavailable, "
                        f"retry after {self.recovery_timeout}s"
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise APIError(f"Circuit breaker: {e}") from e
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"
        
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Fallback response generator
def generate_fallback_response(
    error: Exception,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate appropriate fallback response based on error type
    """
    agent_name = context.get("current_agent", "assistant")
    contact_name = context.get("contact_name", "there")
    
    fallback_messages = {
        APIError: f"Hi {contact_name}, I'm experiencing some technical difficulties. "
                  f"Can you please try again in a moment?",
        
        RateLimitError: f"I apologize {contact_name}, but I'm currently helping many customers. "
                       f"Please give me a moment to catch up.",
        
        GraphRecursionError: f"I think we might be going in circles, {contact_name}. "
                            f"Let me summarize what we've discussed so far.",
        
        TimeoutError: f"Sorry {contact_name}, that took longer than expected. "
                     f"Let me try a different approach.",
    }
    
    # Get appropriate message
    message = fallback_messages.get(
        type(error),
        f"I apologize for the inconvenience, {contact_name}. "
        f"Let me connect you with someone who can help better."
    )
    
    return {
        "messages": [{
            "role": "assistant",
            "content": message
        }],
        "error": str(error),
        "error_type": type(error).__name__,
        "fallback_used": True
    }


# Error recovery middleware
async def error_recovery_middleware(
    func: Callable,
    state: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Middleware that wraps agent functions with error recovery
    """
    try:
        return await func(state, config)
        
    except RecoverableError as e:
        logger.warning(f"Recoverable error: {e}")
        
        # Generate fallback response
        fallback = generate_fallback_response(e, state)
        
        # Attempt recovery action if specified
        if e.recovery_action == "wait_and_retry":
            fallback["retry_after"] = getattr(e, "retry_after", 60)
        
        return fallback
        
    except Exception as e:
        logger.error(f"Unrecoverable error: {e}", exc_info=True)
        
        # Last resort fallback
        return {
            "messages": [{
                "role": "assistant",
                "content": "I apologize, but I need to transfer you to another representative. "
                          "They'll be able to help you better."
            }],
            "error": str(e),
            "next_agent": "maria",  # Transfer to support
            "should_continue": True
        }


# Export utilities
__all__ = [
    "RecoverableError",
    "APIError", 
    "RateLimitError",
    "with_retry",
    "handle_graph_recursion",
    "CircuitBreaker",
    "generate_fallback_response",
    "error_recovery_middleware"
]