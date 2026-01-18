"""
External Service Failure Handling

This module implements retry logic with exponential backoff, circuit breaker patterns,
and graceful degradation for external service failures.

Validates: Requirements 8.4, 9.1, 9.2
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from enum import Enum
import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service is failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service has recovered


class ExternalServiceError(Exception):
    """Base exception for external service errors."""
    
    def __init__(self, message: str, service_name: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.service_name = service_name
        self.retry_after = retry_after


class RetryableError(ExternalServiceError):
    """Error that can be retried."""
    pass


class NonRetryableError(ExternalServiceError):
    """Error that should not be retried."""
    pass


class CircuitBreakerOpenError(ExternalServiceError):
    """Error when circuit breaker is open."""
    pass


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception


class CircuitBreaker:
    """Circuit breaker implementation for external services."""
    
    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        self.state = ServiceState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution."""
        now = datetime.now()
        
        if self.state == ServiceState.CLOSED:
            return True
        elif self.state == ServiceState.OPEN:
            if self.next_attempt_time and now >= self.next_attempt_time:
                self.state = ServiceState.HALF_OPEN
                logger.info(f"Circuit breaker for {self.service_name} moving to HALF_OPEN")
                return True
            return False
        elif self.state == ServiceState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == ServiceState.HALF_OPEN:
            logger.info(f"Circuit breaker for {self.service_name} recovered, moving to CLOSED")
            self.state = ServiceState.CLOSED
        
        self.failure_count = 0
        self.last_failure_time = None
        self.next_attempt_time = None
    
    def record_failure(self, exception: Exception):
        """Record a failed operation."""
        if not isinstance(exception, self.config.expected_exception):
            return
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == ServiceState.HALF_OPEN:
            # Failed during recovery attempt, go back to OPEN
            self.state = ServiceState.OPEN
            self.next_attempt_time = datetime.now() + timedelta(seconds=self.config.recovery_timeout)
            logger.warning(f"Circuit breaker for {self.service_name} failed during recovery, back to OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            # Too many failures, open the circuit
            self.state = ServiceState.OPEN
            self.next_attempt_time = datetime.now() + timedelta(seconds=self.config.recovery_timeout)
            logger.error(f"Circuit breaker for {self.service_name} opened due to {self.failure_count} failures")


class ExternalServiceHandler:
    """Handler for external service calls with retry logic and circuit breaker."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_configs: Dict[str, Dict[str, Any]] = {
            'github_api': {
                'retry': RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0),
                'circuit_breaker': CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
            },
            'http_scraper': {
                'retry': RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0),
                'circuit_breaker': CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30)
            }
        }
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            config = self.service_configs.get(service_name, {}).get('circuit_breaker')
            if not config:
                config = CircuitBreakerConfig()
            
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        
        return self.circuit_breakers[service_name]
    
    async def execute_with_retry(
        self,
        service_name: str,
        operation: Callable[[], T],
        retry_config: Optional[RetryConfig] = None
    ) -> T:
        """
        Execute an operation with retry logic and circuit breaker.
        
        Args:
            service_name: Name of the external service
            operation: Async function to execute
            retry_config: Optional retry configuration
            
        Returns:
            Result of the operation
            
        Raises:
            CircuitBreakerOpenError: When circuit breaker is open
            NonRetryableError: When error should not be retried
            RetryableError: When all retry attempts are exhausted
        """
        circuit_breaker = self.get_circuit_breaker(service_name)
        
        # Check circuit breaker
        if not circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker for {service_name} is open",
                service_name,
                retry_after=60
            )
        
        # Use service-specific retry config or provided config
        if retry_config is None:
            retry_config = self.service_configs.get(service_name, {}).get('retry', RetryConfig())
        
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                result = await operation()
                circuit_breaker.record_success()
                return result
                
            except Exception as e:
                last_exception = e
                circuit_breaker.record_failure(e)
                
                # Classify the error
                error_type = self._classify_error(e, service_name)
                
                if isinstance(error_type, NonRetryableError):
                    logger.warning(f"Non-retryable error for {service_name}: {e}")
                    raise error_type
                
                # Check if we should retry
                if attempt < retry_config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, retry_config)
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_config.max_attempts} failed for {service_name}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {retry_config.max_attempts} attempts failed for {service_name}: {e}")
        
        # All attempts failed
        if isinstance(last_exception, httpx.HTTPStatusError):
            raise RetryableError(
                f"All retry attempts failed for {service_name}: {last_exception}",
                service_name
            )
        else:
            raise RetryableError(
                f"All retry attempts failed for {service_name}: {last_exception}",
                service_name
            )
    
    def _classify_error(self, error: Exception, service_name: str) -> ExternalServiceError:
        """Classify error as retryable or non-retryable."""
        
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            
            # Non-retryable client errors
            if status_code in [400, 401, 403, 404, 422]:
                if status_code == 403 and service_name == 'github_api':
                    # Check if it's rate limiting (retryable) or access forbidden (non-retryable)
                    rate_limit_remaining = error.response.headers.get("X-RateLimit-Remaining")
                    if rate_limit_remaining == "0":
                        # Rate limit - retryable with delay
                        retry_after = int(error.response.headers.get("Retry-After", "60"))
                        return RetryableError(
                            f"GitHub API rate limit exceeded",
                            service_name,
                            retry_after=retry_after
                        )
                    else:
                        # Access forbidden - non-retryable
                        return NonRetryableError(
                            f"Access forbidden to {service_name}",
                            service_name
                        )
                else:
                    return NonRetryableError(
                        f"Client error {status_code} for {service_name}",
                        service_name
                    )
            
            # Retryable server errors
            elif status_code >= 500:
                return RetryableError(
                    f"Server error {status_code} for {service_name}",
                    service_name
                )
        
        # Network errors are generally retryable
        elif isinstance(error, (httpx.TimeoutException, httpx.ConnectError)):
            return RetryableError(
                f"Network error for {service_name}: {error}",
                service_name
            )
        
        # Default to retryable for unknown errors
        return RetryableError(
            f"Unknown error for {service_name}: {error}",
            service_name
        )
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for exponential backoff with jitter."""
        delay = config.base_delay * (config.exponential_base ** attempt)
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            # Add random jitter (±25%)
            import random
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 100ms delay
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get current status of a service."""
        circuit_breaker = self.circuit_breakers.get(service_name)
        
        if not circuit_breaker:
            return {
                "service_name": service_name,
                "state": "unknown",
                "failure_count": 0,
                "last_failure_time": None
            }
        
        return {
            "service_name": service_name,
            "state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "last_failure_time": circuit_breaker.last_failure_time.isoformat() if circuit_breaker.last_failure_time else None,
            "next_attempt_time": circuit_breaker.next_attempt_time.isoformat() if circuit_breaker.next_attempt_time else None
        }
    
    def reset_circuit_breaker(self, service_name: str):
        """Reset circuit breaker for a service (for testing/admin purposes)."""
        if service_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[service_name]
            circuit_breaker.state = ServiceState.CLOSED
            circuit_breaker.failure_count = 0
            circuit_breaker.last_failure_time = None
            circuit_breaker.next_attempt_time = None
            logger.info(f"Circuit breaker for {service_name} manually reset")


# Global instance
external_service_handler = ExternalServiceHandler()


async def with_retry(service_name: str, operation: Callable[[], T], retry_config: Optional[RetryConfig] = None) -> T:
    """
    Convenience function for executing operations with retry logic.
    
    Args:
        service_name: Name of the external service
        operation: Async function to execute
        retry_config: Optional retry configuration
        
    Returns:
        Result of the operation
    """
    return await external_service_handler.execute_with_retry(service_name, operation, retry_config)


def create_fallback_response(service_name: str, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create a fallback response for when external services fail.
    
    Args:
        service_name: Name of the failed service
        error: The error that occurred
        context: Additional context information
        
    Returns:
        Fallback response dictionary
    """
    fallback_data = {
        "service_name": service_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "fallback_active": True,
        "timestamp": datetime.now().isoformat()
    }
    
    if context:
        fallback_data["context"] = context
    
    # Service-specific fallback logic
    if service_name == 'github_api':
        fallback_data.update({
            "detected_components": [],
            "failed_detections": [f"GitHub API unavailable: {error}"],
            "detection_metadata": {
                "analysis_type": "github",
                "fallback_reason": "github_api_failure",
                "original_error": str(error)
            }
        })
    elif service_name == 'http_scraper':
        fallback_data.update({
            "detected_components": [],
            "failed_detections": [f"HTTP scraping unavailable: {error}"],
            "detection_metadata": {
                "analysis_type": "website",
                "fallback_reason": "http_scraper_failure",
                "original_error": str(error)
            }
        })
    
    return fallback_data