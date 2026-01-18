# External Service Failure Handling

This document describes the comprehensive external service failure handling infrastructure implemented for the StackDebt system.

## Overview

The external service failure handling system provides:

- **Retry Logic with Exponential Backoff**: Automatically retries failed requests with increasing delays
- **Circuit Breaker Pattern**: Prevents cascading failures by temporarily stopping requests to failing services
- **Graceful Degradation**: Provides fallback responses when services are unavailable
- **Service Health Monitoring**: Tracks service status and failure patterns

## Architecture

### Components

1. **ExternalServiceHandler**: Main orchestrator for retry logic and circuit breakers
2. **CircuitBreaker**: Implements circuit breaker pattern for individual services
3. **RetryConfig**: Configuration for retry behavior
4. **CircuitBreakerConfig**: Configuration for circuit breaker behavior
5. **Error Classification**: Categorizes errors as retryable or non-retryable

### Service Integration

The system is integrated into:
- **GitHubAnalyzer**: Handles GitHub API failures
- **HTTPHeaderScraper**: Handles website scraping failures
- **Main API**: Provides monitoring and management endpoints

## Retry Logic

### Configuration

```python
RetryConfig(
    max_attempts=3,        # Maximum retry attempts
    base_delay=1.0,        # Base delay in seconds
    max_delay=60.0,        # Maximum delay cap
    exponential_base=2.0,  # Exponential backoff multiplier
    jitter=True           # Add random jitter to delays
)
```

### Exponential Backoff

Delays are calculated as: `base_delay * (exponential_base ^ attempt)`

With jitter enabled, a random variation of ±25% is added to prevent thundering herd problems.

### Error Classification

Errors are classified as:

- **Retryable**: Network timeouts, connection errors, 5xx HTTP errors, GitHub rate limits
- **Non-retryable**: 4xx HTTP errors (except rate limits), authentication failures, invalid URLs

## Circuit Breaker Pattern

### States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Service is failing, requests are rejected immediately
3. **HALF_OPEN**: Testing if service has recovered

### Configuration

```python
CircuitBreakerConfig(
    failure_threshold=5,    # Failures needed to open circuit
    recovery_timeout=60,    # Seconds before attempting recovery
    expected_exception=Exception  # Exception types to track
)
```

### State Transitions

- **CLOSED → OPEN**: After `failure_threshold` consecutive failures
- **OPEN → HALF_OPEN**: After `recovery_timeout` seconds
- **HALF_OPEN → CLOSED**: On successful operation
- **HALF_OPEN → OPEN**: On failed operation during recovery

## Service-Specific Configurations

### GitHub API

```python
'github_api': {
    'retry': RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0),
    'circuit_breaker': CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
}
```

**Special Handling**:
- Rate limit detection via `X-RateLimit-Remaining` header
- Automatic retry with `Retry-After` delay
- Private repository detection (non-retryable)

### HTTP Scraper

```python
'http_scraper': {
    'retry': RetryConfig(max_attempts=2, base_delay=1.0, max_delay=10.0),
    'circuit_breaker': CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30)
}
```

**Special Handling**:
- Website blocking detection (non-retryable)
- DNS resolution failures (retryable)
- SSL certificate errors (retryable)

## Fallback Mechanisms

When all retries are exhausted or circuit breakers are open, the system provides fallback responses:

### GitHub API Fallback

```json
{
  "detected_components": [],
  "failed_detections": ["GitHub API unavailable: <error>"],
  "detection_metadata": {
    "analysis_type": "github",
    "fallback_reason": "github_api_failure",
    "original_error": "<error_details>"
  }
}
```

### HTTP Scraper Fallback

```json
{
  "detected_components": [],
  "failed_detections": ["HTTP scraping unavailable: <error>"],
  "detection_metadata": {
    "analysis_type": "website",
    "fallback_reason": "http_scraper_failure",
    "original_error": "<error_details>"
  }
}
```

## Monitoring and Management

### API Endpoints

#### Get All Services Status
```
GET /api/external-services/status
```

Returns status of all external services including circuit breaker states.

#### Get Individual Service Status
```
GET /api/external-services/{service_name}/status
```

Returns detailed status for a specific service.

#### Reset Circuit Breaker
```
POST /api/external-services/{service_name}/reset
```

Manually resets the circuit breaker for a service.

### Status Information

Each service status includes:
- **service_name**: Name of the service
- **state**: Circuit breaker state (closed/open/half_open/unknown)
- **failure_count**: Number of recent failures
- **last_failure_time**: Timestamp of last failure
- **next_attempt_time**: When circuit breaker will attempt recovery

## Usage Examples

### Basic Usage

```python
from app.external_service_handler import external_service_handler

async def my_operation():
    # Your external service call here
    return await some_external_api_call()

# Execute with retry and circuit breaker
result = await external_service_handler.execute_with_retry(
    service_name='my_service',
    operation=my_operation
)
```

### Custom Configuration

```python
from app.external_service_handler import RetryConfig

custom_config = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=20.0
)

result = await external_service_handler.execute_with_retry(
    service_name='my_service',
    operation=my_operation,
    retry_config=custom_config
)
```

### Error Handling

```python
from app.external_service_handler import (
    RetryableError,
    NonRetryableError,
    CircuitBreakerOpenError
)

try:
    result = await external_service_handler.execute_with_retry(
        service_name='my_service',
        operation=my_operation
    )
except CircuitBreakerOpenError:
    # Circuit breaker is open, use fallback
    result = create_fallback_response()
except NonRetryableError:
    # Error should not be retried, handle appropriately
    raise
except RetryableError:
    # All retries exhausted, use fallback
    result = create_fallback_response()
```

## Testing

The system includes comprehensive tests covering:

- Retry logic with various failure scenarios
- Circuit breaker state transitions
- Error classification accuracy
- Exponential backoff calculations
- Fallback response generation
- Service status monitoring

Run tests with:
```bash
python -m pytest tests/test_external_service_handler.py -v
```

## Performance Considerations

### Retry Delays

- **Base delays**: Start small (1-2 seconds) to avoid unnecessary delays
- **Max delays**: Cap at reasonable values (30-60 seconds) to prevent excessive waits
- **Jitter**: Always enabled to prevent thundering herd problems

### Circuit Breaker Thresholds

- **Failure thresholds**: Set based on service reliability (3-5 failures)
- **Recovery timeouts**: Balance between quick recovery and avoiding flapping (30-60 seconds)

### Memory Usage

- Circuit breakers maintain minimal state (failure count, timestamps)
- No persistent storage required
- Automatic cleanup of old failure data

## Compliance with Requirements

This implementation validates the following requirements:

- **Requirement 8.4**: External service failures return appropriate error messages rather than crashing
- **Requirement 9.1**: Clear error messages for private/inaccessible repositories
- **Requirement 9.2**: Inform users about unreachable websites with alternatives

## Future Enhancements

Potential improvements include:

1. **Persistent Circuit Breaker State**: Store state across application restarts
2. **Adaptive Thresholds**: Adjust failure thresholds based on service patterns
3. **Metrics Integration**: Export metrics to monitoring systems
4. **Distributed Circuit Breakers**: Coordinate circuit breaker state across multiple instances
5. **Custom Retry Strategies**: Support for different retry patterns (linear, polynomial)