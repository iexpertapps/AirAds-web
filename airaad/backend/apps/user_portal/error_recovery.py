import time
import random
from typing import Callable, Any, Optional, Dict
from functools import wraps
from django.core.cache import cache
from django.conf import settings
import logging

from .logging import structured_logger

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Prevents cascading failures by temporarily disabling failing operations.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
        # Cache key for distributed circuit breaker state
        self.cache_key = None
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key if not set
            if not self.cache_key:
                self.cache_key = f"circuit_breaker:{func.__module__}.{func.__name__}"
            
            # Load state from cache (for distributed systems)
            self._load_state()
            
            # Check if circuit is open
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                    self._save_state()
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker is open for {func.__name__}"
                    )
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Reset failure count on success
                if self.state == 'HALF_OPEN':
                    self.state = 'CLOSED'
                    self.failure_count = 0
                
                self._save_state()
                return result
                
            except self.expected_exception as e:
                # Record failure
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # Open circuit if threshold reached
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
                    structured_logger.warning(
                        f"Circuit breaker opened for {func.__name__}",
                        failure_count=self.failure_count,
                        threshold=self.failure_threshold,
                        function=func.__name__
                    )
                
                self._save_state()
                raise
        
        return wrapper
    
    def _load_state(self):
        """Load circuit breaker state from cache."""
        if self.cache_key:
            state_data = cache.get(self.cache_key)
            if state_data:
                self.state = state_data.get('state', 'CLOSED')
                self.failure_count = state_data.get('failure_count', 0)
                self.last_failure_time = state_data.get('last_failure_time')
    
    def _save_state(self):
        """Save circuit breaker state to cache."""
        if self.cache_key:
            state_data = {
                'state': self.state,
                'failure_count': self.failure_count,
                'last_failure_time': self.last_failure_time,
            }
            cache.set(self.cache_key, state_data, timeout=self.recovery_timeout * 2)
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)


class RetryWithBackoff:
    """
    Retry mechanism with exponential backoff.
    """
    
    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True,
                 retry_on: tuple = (Exception,)):
        """
        Initialize retry mechanism.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to prevent thundering herd
            retry_on: Exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply retry mechanism to a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_attempts):
                try:
                    return func(*args, **kwargs)
                
                except self.retry_on as e:
                    last_exception = e
                    
                    if attempt == self.max_attempts - 1:
                        # Last attempt, re-raise exception
                        structured_logger.error(
                            f"Retry failed for {func.__name__}",
                            attempts=attempt + 1,
                            max_attempts=self.max_attempts,
                            error=str(e),
                            function=func.__name__
                        )
                        raise
                    
                    # Calculate delay
                    delay = self._calculate_delay(attempt)
                    
                    structured_logger.warning(
                        f"Retrying {func.__name__}",
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        delay=delay,
                        error=str(e),
                        function=func.__name__
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached
            raise last_exception
        
        return wrapper
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class ErrorRecoveryStrategy:
    """
    Error recovery strategies for different types of failures.
    """
    
    @staticmethod
    def database_connection_error(func: Callable) -> Callable:
        """Recovery strategy for database connection errors."""
        @RetryWithBackoff(max_attempts=3, base_delay=0.5, max_delay=10.0)
        @CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def external_api_error(func: Callable) -> Callable:
        """Recovery strategy for external API errors."""
        @RetryWithBackoff(max_attempts=5, base_delay=1.0, max_delay=60.0)
        @CircuitBreaker(failure_threshold=5, recovery_timeout=120)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def cache_error(func: Callable) -> Callable:
        """Recovery strategy for cache errors."""
        @RetryWithBackoff(max_attempts=2, base_delay=0.1, max_delay=1.0)
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Cache errors should not break the main flow
                structured_logger.warning(
                    f"Cache operation failed, continuing without cache",
                    error=str(e),
                    function=func.__name__
                )
                # Return None or a default value based on context
                return None
        return wrapper
    
    @staticmethod
    def timeout_error(func: Callable) -> Callable:
        """Recovery strategy for timeout errors."""
        @RetryWithBackoff(max_attempts=2, base_delay=0.5, max_delay=5.0)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ErrorRecoveryManager:
    """
    Central error recovery management system.
    """
    
    def __init__(self):
        self.strategies = {
            'database': ErrorRecoveryStrategy.database_connection_error,
            'external_api': ErrorRecoveryStrategy.external_api_error,
            'cache': ErrorRecoveryStrategy.cache_error,
            'timeout': ErrorRecoveryStrategy.timeout_error,
        }
    
    def apply_strategy(self, strategy_name: str, func: Callable) -> Callable:
        """Apply a specific recovery strategy to a function."""
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown recovery strategy: {strategy_name}")
        
        return self.strategies[strategy_name](func)
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        status = {}
        
        # Get all circuit breaker cache keys
        for key in cache.keys('circuit_breaker:*'):
            state_data = cache.get(key)
            if state_data:
                function_name = key.replace('circuit_breaker:', '')
                status[function_name] = {
                    'state': state_data.get('state', 'CLOSED'),
                    'failure_count': state_data.get('failure_count', 0),
                    'last_failure_time': state_data.get('last_failure_time'),
                }
        
        return status
    
    def reset_circuit_breaker(self, function_name: str) -> bool:
        """Reset a specific circuit breaker."""
        cache_key = f"circuit_breaker:{function_name}"
        cache.delete(cache_key)
        return True


# Global instances
error_recovery_manager = ErrorRecoveryManager()
