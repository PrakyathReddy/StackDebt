"""
Unit tests for external service failure handling infrastructure.

Tests the retry logic, circuit breaker, and fallback mechanisms.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import httpx
from datetime import datetime, timedelta

from app.external_service_handler import (
    ExternalServiceHandler,
    RetryConfig,
    CircuitBreakerConfig,
    CircuitBreaker,
    ServiceState,
    RetryableError,
    NonRetryableError,
    CircuitBreakerOpenError,
    create_fallback_response
)


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retries."""
        handler = ExternalServiceHandler()
        
        mock_operation = AsyncMock(return_value="success")
        
        result = await handler.execute_with_retry(
            service_name='test_service',
            operation=mock_operation
        )
        
        assert result == "success"
        assert mock_operation.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry logic for transient failures."""
        handler = ExternalServiceHandler()
        
        # Mock operation that fails twice then succeeds
        mock_operation = AsyncMock(side_effect=[
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            "success"
        ])
        
        result = await handler.execute_with_retry(
            service_name='test_service',
            operation=mock_operation,
            retry_config=RetryConfig(max_attempts=3, base_delay=0.01)  # Fast retry for testing
        )
        
        assert result == "success"
        assert mock_operation.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        handler = ExternalServiceHandler()
        
        mock_operation = AsyncMock(side_effect=httpx.TimeoutException("Persistent timeout"))
        
        with pytest.raises(RetryableError):
            await handler.execute_with_retry(
                service_name='test_service',
                operation=mock_operation,
                retry_config=RetryConfig(max_attempts=2, base_delay=0.01)
            )
        
        assert mock_operation.call_count == 2
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """Test that non-retryable errors are not retried."""
        handler = ExternalServiceHandler()
        
        # Mock 404 error (non-retryable)
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_operation = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", "https://api.github.com/repos/user/repo"),
            response=mock_response
        ))
        
        with pytest.raises(NonRetryableError):
            await handler.execute_with_retry(
                service_name='github_api',
                operation=mock_operation
            )
        
        # Should only be called once (no retries)
        assert mock_operation.call_count == 1


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        breaker = CircuitBreaker("test_service", config)
        
        # Initially closed
        assert breaker.state == ServiceState.CLOSED
        assert breaker.can_execute() is True
        
        # Record failures
        breaker.record_failure(Exception("Error 1"))
        assert breaker.state == ServiceState.CLOSED  # Still closed
        
        breaker.record_failure(Exception("Error 2"))
        assert breaker.state == ServiceState.OPEN  # Now open
        assert breaker.can_execute() is False
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        breaker = CircuitBreaker("test_service", config)
        
        # Trigger circuit breaker
        breaker.record_failure(Exception("Error"))
        assert breaker.state == ServiceState.OPEN
        
        # Wait for recovery timeout
        import time
        time.sleep(0.2)
        
        # Should allow execution (half-open)
        assert breaker.can_execute() is True
        assert breaker.state == ServiceState.HALF_OPEN
        
        # Successful operation should close circuit
        breaker.record_success()
        assert breaker.state == ServiceState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with retry handler."""
        handler = ExternalServiceHandler()
        
        # Configure circuit breaker with low threshold for testing
        handler.service_configs['test_service'] = {
            'circuit_breaker': CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        }
        
        mock_operation = AsyncMock(side_effect=Exception("Persistent error"))
        
        # First few calls should fail and trigger circuit breaker
        for _ in range(3):
            with pytest.raises((RetryableError, CircuitBreakerOpenError)):
                await handler.execute_with_retry(
                    service_name='test_service',
                    operation=mock_operation,
                    retry_config=RetryConfig(max_attempts=1, base_delay=0.01)
                )
        
        # Circuit breaker should now be open
        breaker = handler.get_circuit_breaker('test_service')
        assert breaker.state == ServiceState.OPEN


class TestErrorClassification:
    """Test error classification logic."""
    
    def test_github_rate_limit_classification(self):
        """Test GitHub rate limit error classification."""
        handler = ExternalServiceHandler()
        
        # Mock rate limit response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "0", "Retry-After": "60"}
        
        error = httpx.HTTPStatusError(
            "Rate limit exceeded",
            request=httpx.Request("GET", "https://api.github.com"),
            response=mock_response
        )
        
        classified_error = handler._classify_error(error, 'github_api')
        assert isinstance(classified_error, RetryableError)
        assert classified_error.retry_after == 60
    
    def test_github_access_forbidden_classification(self):
        """Test GitHub access forbidden error classification."""
        handler = ExternalServiceHandler()
        
        # Mock access forbidden response (not rate limit)
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "100"}
        
        error = httpx.HTTPStatusError(
            "Access forbidden",
            request=httpx.Request("GET", "https://api.github.com"),
            response=mock_response
        )
        
        classified_error = handler._classify_error(error, 'github_api')
        assert isinstance(classified_error, NonRetryableError)
    
    def test_network_error_classification(self):
        """Test network error classification."""
        handler = ExternalServiceHandler()
        
        timeout_error = httpx.TimeoutException("Request timeout")
        classified_error = handler._classify_error(timeout_error, 'test_service')
        assert isinstance(classified_error, RetryableError)
        
        connect_error = httpx.ConnectError("Connection refused")
        classified_error = handler._classify_error(connect_error, 'test_service')
        assert isinstance(classified_error, RetryableError)


class TestFallbackMechanisms:
    """Test fallback response creation."""
    
    def test_github_api_fallback_response(self):
        """Test fallback response for GitHub API failures."""
        error = httpx.TimeoutException("GitHub API timeout")
        context = {'repository_url': 'https://github.com/user/repo'}
        
        fallback = create_fallback_response('github_api', error, context)
        
        assert fallback['service_name'] == 'github_api'
        assert fallback['error_type'] == 'TimeoutException'
        assert fallback['fallback_active'] is True
        assert 'detected_components' in fallback
        assert 'failed_detections' in fallback
        assert fallback['detection_metadata']['analysis_type'] == 'github'
    
    def test_http_scraper_fallback_response(self):
        """Test fallback response for HTTP scraper failures."""
        error = httpx.ConnectError("Connection refused")
        context = {'url_analyzed': 'https://example.com'}
        
        fallback = create_fallback_response('http_scraper', error, context)
        
        assert fallback['service_name'] == 'http_scraper'
        assert fallback['error_type'] == 'ConnectError'
        assert fallback['fallback_active'] is True
        assert 'detected_components' in fallback
        assert 'failed_detections' in fallback
        assert fallback['detection_metadata']['analysis_type'] == 'website'


class TestServiceStatusMonitoring:
    """Test service status monitoring functionality."""
    
    def test_service_status_reporting(self):
        """Test service status reporting."""
        handler = ExternalServiceHandler()
        
        # Get status for non-existent service
        status = handler.get_service_status('unknown_service')
        assert status['service_name'] == 'unknown_service'
        assert status['state'] == 'unknown'
        assert status['failure_count'] == 0
        
        # Create a circuit breaker and check status
        breaker = handler.get_circuit_breaker('test_service')
        breaker.record_failure(Exception("Test error"))
        
        status = handler.get_service_status('test_service')
        assert status['service_name'] == 'test_service'
        assert status['state'] == 'closed'  # Still closed after 1 failure
        assert status['failure_count'] == 1
    
    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset."""
        handler = ExternalServiceHandler()
        
        # Trigger circuit breaker
        breaker = handler.get_circuit_breaker('test_service')
        for _ in range(5):  # Default threshold is 5
            breaker.record_failure(Exception("Test error"))
        
        assert breaker.state == ServiceState.OPEN
        
        # Reset circuit breaker
        handler.reset_circuit_breaker('test_service')
        
        assert breaker.state == ServiceState.CLOSED
        assert breaker.failure_count == 0


class TestExponentialBackoff:
    """Test exponential backoff calculation."""
    
    def test_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        handler = ExternalServiceHandler()
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=10.0, jitter=False)
        
        # Test exponential growth
        delay_0 = handler._calculate_delay(0, config)
        delay_1 = handler._calculate_delay(1, config)
        delay_2 = handler._calculate_delay(2, config)
        
        assert delay_0 == 1.0  # base_delay * 2^0
        assert delay_1 == 2.0  # base_delay * 2^1
        assert delay_2 == 4.0  # base_delay * 2^2
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        handler = ExternalServiceHandler()
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
        
        delay = handler._calculate_delay(10, config)  # Would be 1024 without cap
        assert delay == 5.0
    
    def test_jitter_application(self):
        """Test that jitter is applied when enabled."""
        handler = ExternalServiceHandler()
        config = RetryConfig(base_delay=4.0, exponential_base=2.0, max_delay=20.0, jitter=True)
        
        # With jitter, delays should vary
        delays = [handler._calculate_delay(1, config) for _ in range(10)]
        
        # All delays should be different (with high probability)
        assert len(set(delays)) > 1
        
        # All delays should be within jitter range (±25% of 8.0 for attempt 1)
        # base_delay * 2^1 = 4.0 * 2 = 8.0, ±25% = 6.0 to 10.0
        for delay in delays:
            assert 6.0 <= delay <= 10.0