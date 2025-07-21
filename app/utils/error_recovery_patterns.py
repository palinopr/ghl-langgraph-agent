"""
Error recovery patterns for agents with interrupt capability
"""
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from functools import wraps
import asyncio
from datetime import datetime
from langgraph.types import interrupt
from app.utils.simple_logger import get_logger
from app.debug.trace_collector import trace_collector

logger = get_logger("error_recovery")

T = TypeVar('T')


class ErrorRecoveryConfig:
    """Configuration for error recovery behavior"""
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        exponential_backoff: bool = True,
        interrupt_on_critical: bool = True,
        fallback_response: Optional[str] = None
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.interrupt_on_critical = interrupt_on_critical
        self.fallback_response = fallback_response or "I apologize, but I'm having trouble processing your request. Please try again later."


def with_error_recovery(
    config: Optional[ErrorRecoveryConfig] = None,
    error_types: tuple = (Exception,),
    critical_errors: tuple = (KeyError, ValueError, TypeError)
) -> Callable:
    """
    Decorator for agent functions with error recovery and interrupt capability
    
    Args:
        config: Error recovery configuration
        error_types: Tuple of error types to catch and retry
        critical_errors: Tuple of error types that trigger interrupt
    """
    if config is None:
        config = ErrorRecoveryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            contact_id = kwargs.get('state', {}).get('contact_id', 'unknown')
            retries = 0
            last_error = None
            
            while retries <= config.max_retries:
                try:
                    # Log attempt
                    if retries > 0:
                        logger.info(f"Retry attempt {retries} for {func.__name__}")
                        trace_collector.add_event(
                            contact_id,
                            "retry",
                            f"Retrying {func.__name__} (attempt {retries})"
                        )
                    
                    # Execute the function
                    result = await func(*args, **kwargs)
                    
                    # Success - log and return
                    if retries > 0:
                        logger.info(f"Successfully recovered {func.__name__} after {retries} retries")
                    
                    return result
                    
                except critical_errors as e:
                    # Critical error - interrupt for human review
                    error_msg = f"Critical error in {func.__name__}: {type(e).__name__}: {str(e)}"
                    logger.error(error_msg)
                    trace_collector.add_error(contact_id, "critical_error", error_msg)
                    
                    if config.interrupt_on_critical:
                        return interrupt(
                            reason=f"Critical error requiring human intervention: {error_msg}",
                            data={
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "function": func.__name__,
                                "timestamp": datetime.now().isoformat(),
                                "contact_id": contact_id
                            }
                        )
                    else:
                        # Return fallback response
                        return {
                            "messages": [{"role": "assistant", "content": config.fallback_response}],
                            "error_occurred": True,
                            "error_details": error_msg
                        }
                
                except error_types as e:
                    # Recoverable error - retry with backoff
                    last_error = e
                    error_msg = f"Error in {func.__name__}: {type(e).__name__}: {str(e)}"
                    logger.warning(f"{error_msg} - Retry {retries}/{config.max_retries}")
                    trace_collector.add_event(
                        contact_id,
                        "error",
                        error_msg,
                        {"retry_count": retries}
                    )
                    
                    if retries < config.max_retries:
                        # Calculate delay with exponential backoff
                        delay = config.retry_delay
                        if config.exponential_backoff:
                            delay *= (2 ** retries)
                        
                        await asyncio.sleep(delay)
                        retries += 1
                    else:
                        # Max retries exceeded
                        logger.error(f"Max retries exceeded for {func.__name__}")
                        trace_collector.add_error(
                            contact_id,
                            "max_retries_exceeded",
                            f"Failed after {config.max_retries} attempts"
                        )
                        
                        # Return fallback response
                        return {
                            "messages": [{"role": "assistant", "content": config.fallback_response}],
                            "error_occurred": True,
                            "error_details": f"Max retries exceeded: {str(last_error)}"
                        }
            
            # Should not reach here
            return {
                "messages": [{"role": "assistant", "content": config.fallback_response}],
                "error_occurred": True
            }
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for preventing cascading failures
    """
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        """
        if self.state == "open":
            # Check if we should try half-open
            if self.last_failure_time and \
               (datetime.now().timestamp() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half-open"
                logger.info(f"Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            # Try to execute
            result = await func(*args, **kwargs)
            
            # Success - reset on half-open
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker reset to closed")
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now().timestamp()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
                
            raise e


# Preset configurations for common scenarios
STRICT_RECOVERY = ErrorRecoveryConfig(
    max_retries=5,
    retry_delay=0.5,
    exponential_backoff=True,
    interrupt_on_critical=True
)

LENIENT_RECOVERY = ErrorRecoveryConfig(
    max_retries=3,
    retry_delay=1.0,
    exponential_backoff=False,
    interrupt_on_critical=False,
    fallback_response="Let me try a different approach. How can I help you today?"
)

NO_RETRY = ErrorRecoveryConfig(
    max_retries=0,
    interrupt_on_critical=True
)


# Helper functions for common error scenarios
async def safe_llm_call(
    llm_func: Callable,
    fallback_response: str,
    contact_id: str = "unknown"
) -> Union[str, Dict[str, Any]]:
    """
    Safely call an LLM with automatic fallback
    """
    try:
        return await llm_func()
    except Exception as e:
        logger.error(f"LLM call failed: {str(e)}")
        trace_collector.add_error(contact_id, "llm_error", str(e))
        return {"role": "assistant", "content": fallback_response}


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator specifically for API calls with smart retry logic
    """
    return with_error_recovery(
        config=ErrorRecoveryConfig(
            max_retries=3,
            retry_delay=2.0,
            exponential_backoff=True,
            interrupt_on_critical=False,
            fallback_response="I'm having trouble accessing the system. Please try again in a moment."
        ),
        error_types=(ConnectionError, TimeoutError, Exception),
        critical_errors=(KeyError, ValueError)
    )(func)


# Export utilities
__all__ = [
    "ErrorRecoveryConfig",
    "with_error_recovery",
    "CircuitBreaker",
    "STRICT_RECOVERY",
    "LENIENT_RECOVERY",
    "NO_RETRY",
    "safe_llm_call",
    "handle_api_errors"
]