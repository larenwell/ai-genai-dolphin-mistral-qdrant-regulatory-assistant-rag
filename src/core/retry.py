"""
Retry Logic Module

Provides retry decorators and utilities with exponential backoff.
"""

import time
import random
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
from .logger import get_logger
from .exceptions import RAGSystemError

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    
    Returns:
        Decorated function
    
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def my_function():
            # Function that may fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            initial_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        
                        # Add jitter if enabled
                        if jitter:
                            delay = delay * (0.5 + random.random() * 0.5)
                        
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        
                        # Call on_retry callback if provided
                        if on_retry:
                            try:
                                on_retry(e, attempt + 1)
                            except Exception as callback_error:
                                logger.error(f"Error in retry callback: {callback_error}")
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {str(e)}"
                        )
                        raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_on_connection_error(
    max_retries: int = 3,
    initial_delay: float = 2.0
):
    """
    Decorator to retry on connection errors specifically.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
    
    Returns:
        Decorated function
    """
    connection_exceptions = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        exceptions=connection_exceptions
    )


def retry_on_api_error(
    max_retries: int = 3,
    initial_delay: float = 1.0
):
    """
    Decorator to retry on API errors (rate limits, temporary failures).
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
    
    Returns:
        Decorated function
    """
    api_exceptions = (
        Exception,  # Catch all for now, can be more specific
    )
    
    def on_retry_callback(exception: Exception, attempt: int):
        """Log API error details."""
        error_msg = str(exception)
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            logger.warning(f"Rate limit detected, waiting longer before retry {attempt}")
        elif "timeout" in error_msg.lower():
            logger.warning(f"Timeout detected, retrying {attempt}")
    
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        exceptions=api_exceptions,
        on_retry=on_retry_callback
    )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests to a failing service
    after a threshold of failures is reached.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise RAGSystemError(
                    "Circuit breaker is OPEN. Service unavailable.",
                    error_code="CIRCUIT_BREAKER_OPEN"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == "half_open":
            logger.info("Circuit breaker reset to CLOSED state")
            self.state = "closed"
        
        self.failure_count = 0
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != "open":
                logger.error(
                    f"Circuit breaker OPENED after {self.failure_count} failures. "
                    f"Will retry after {self.recovery_timeout}s"
                )
                self.state = "open"

