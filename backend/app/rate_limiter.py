"""
Rate limiting middleware for StackDebt API.

Implements rate limiting to prevent abuse while maintaining good user experience.
Validates: Requirements 8.5
"""

import time
import asyncio
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window approach.
    
    This implementation provides rate limiting functionality to prevent abuse
    while maintaining good user experience for normal usage patterns.
    """
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        """
        Initialize rate limiter with configurable limits.
        
        Args:
            requests_per_minute: Maximum requests per minute per IP
            requests_per_hour: Maximum requests per hour per IP
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Storage for request timestamps: {ip: [(timestamp, window_type), ...]}
        self.request_history: Dict[str, list] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, client_ip: str) -> Tuple[bool, Optional[dict]]:
        """
        Check if a request from the given IP is allowed.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
            rate_limit_info contains current usage and limits
        """
        async with self._lock:
            current_time = time.time()
            
            # Clean up old entries and get current counts
            minute_count, hour_count = await self._cleanup_and_count(client_ip, current_time)
            
            # Check limits
            minute_exceeded = minute_count >= self.requests_per_minute
            hour_exceeded = hour_count >= self.requests_per_hour
            
            rate_limit_info = {
                "requests_per_minute_limit": self.requests_per_minute,
                "requests_per_minute_remaining": max(0, self.requests_per_minute - minute_count),
                "requests_per_hour_limit": self.requests_per_hour,
                "requests_per_hour_remaining": max(0, self.requests_per_hour - hour_count),
                "reset_time_minute": int(current_time + 60),
                "reset_time_hour": int(current_time + 3600),
                "current_minute_count": minute_count,
                "current_hour_count": hour_count
            }
            
            if minute_exceeded or hour_exceeded:
                # Rate limit exceeded
                exceeded_type = "minute" if minute_exceeded else "hour"
                logger.warning(
                    f"Rate limit exceeded for IP {client_ip}: "
                    f"{minute_count}/min, {hour_count}/hour (exceeded: {exceeded_type})"
                )
                return False, rate_limit_info
            
            # Record this request
            if client_ip not in self.request_history:
                self.request_history[client_ip] = []
            
            self.request_history[client_ip].append(current_time)
            
            logger.debug(
                f"Request allowed for IP {client_ip}: "
                f"{minute_count + 1}/min, {hour_count + 1}/hour"
            )
            
            return True, rate_limit_info
    
    async def _cleanup_and_count(self, client_ip: str, current_time: float) -> Tuple[int, int]:
        """
        Clean up old entries and count current requests within time windows.
        
        Args:
            client_ip: Client IP address
            current_time: Current timestamp
            
        Returns:
            Tuple of (minute_count, hour_count)
        """
        if client_ip not in self.request_history:
            return 0, 0
        
        # Remove entries older than 1 hour
        one_hour_ago = current_time - 3600
        one_minute_ago = current_time - 60
        
        # Filter out old entries
        recent_requests = [
            timestamp for timestamp in self.request_history[client_ip]
            if timestamp > one_hour_ago
        ]
        
        self.request_history[client_ip] = recent_requests
        
        # Count requests in the last minute and hour
        minute_count = sum(1 for timestamp in recent_requests if timestamp > one_minute_ago)
        hour_count = len(recent_requests)
        
        return minute_count, hour_count
    
    async def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request, handling proxies.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address as string
        """
        # Check for forwarded headers (common in production behind proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def create_rate_limit_response(self, rate_limit_info: dict) -> JSONResponse:
        """
        Create a rate limit exceeded response with helpful information.
        
        Args:
            rate_limit_info: Rate limit information dictionary
            
        Returns:
            JSONResponse with rate limit error details
        """
        # Determine which limit was exceeded
        minute_exceeded = rate_limit_info["requests_per_minute_remaining"] == 0
        hour_exceeded = rate_limit_info["requests_per_hour_remaining"] == 0
        
        if minute_exceeded:
            reset_time = rate_limit_info["reset_time_minute"]
            limit_type = "per minute"
            current_count = rate_limit_info["current_minute_count"]
            limit_value = rate_limit_info["requests_per_minute_limit"]
        else:
            reset_time = rate_limit_info["reset_time_hour"]
            limit_type = "per hour"
            current_count = rate_limit_info["current_hour_count"]
            limit_value = rate_limit_info["requests_per_hour_limit"]
        
        wait_seconds = reset_time - int(time.time())
        
        response_data = {
            "detail": {
                "message": f"Rate limit exceeded: too many requests {limit_type}",
                "error": "RateLimitExceeded",
                "rate_limit_info": {
                    "limit_type": limit_type,
                    "current_count": current_count,
                    "limit_value": limit_value,
                    "reset_in_seconds": max(0, wait_seconds),
                    "reset_time": reset_time
                },
                "suggestions": [
                    f"Wait {max(1, wait_seconds)} seconds before making another request",
                    "Reduce the frequency of your requests",
                    "Consider implementing request caching on your end",
                    "Contact support if you need higher rate limits"
                ]
            }
        }
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit-Minute": str(rate_limit_info["requests_per_minute_limit"]),
            "X-RateLimit-Remaining-Minute": str(rate_limit_info["requests_per_minute_remaining"]),
            "X-RateLimit-Limit-Hour": str(rate_limit_info["requests_per_hour_limit"]),
            "X-RateLimit-Remaining-Hour": str(rate_limit_info["requests_per_hour_remaining"]),
            "X-RateLimit-Reset-Minute": str(rate_limit_info["reset_time_minute"]),
            "X-RateLimit-Reset-Hour": str(rate_limit_info["reset_time_hour"]),
            "Retry-After": str(max(1, wait_seconds))
        }
        
        return JSONResponse(
            status_code=429,
            content=response_data,
            headers=headers
        )


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=60,  # Allow 60 requests per minute (1 per second average)
    requests_per_hour=1000   # Allow 1000 requests per hour for burst usage
)


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for FastAPI.
    
    This middleware checks rate limits before processing requests and
    returns appropriate responses for rate limit violations.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in the chain
        
    Returns:
        Response from next handler or rate limit error response
    """
    # Skip rate limiting for health check endpoints
    if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    client_ip = await rate_limiter.get_client_ip(request)
    
    # Check rate limits
    is_allowed, rate_limit_info = await rate_limiter.is_allowed(client_ip)
    
    if not is_allowed:
        # Rate limit exceeded - return error response
        return await rate_limiter.create_rate_limit_response(rate_limit_info)
    
    # Add rate limit headers to successful responses
    response = await call_next(request)
    
    # Add rate limit information to response headers
    if rate_limit_info:
        response.headers["X-RateLimit-Limit-Minute"] = str(rate_limit_info["requests_per_minute_limit"])
        response.headers["X-RateLimit-Remaining-Minute"] = str(rate_limit_info["requests_per_minute_remaining"])
        response.headers["X-RateLimit-Limit-Hour"] = str(rate_limit_info["requests_per_hour_limit"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(rate_limit_info["requests_per_hour_remaining"])
        response.headers["X-RateLimit-Reset-Minute"] = str(rate_limit_info["reset_time_minute"])
        response.headers["X-RateLimit-Reset-Hour"] = str(rate_limit_info["reset_time_hour"])
    
    return response