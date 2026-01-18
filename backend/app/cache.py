"""
Request caching system for StackDebt API.

Implements in-memory caching for repeated analyses to improve performance
and reduce load on external services and database.

Validates: Requirements 8.1, 8.2, 8.5
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.schemas import AnalysisResponse

logger = logging.getLogger(__name__)


class AnalysisCache:
    """
    In-memory cache for analysis results with TTL and size limits.
    
    This cache stores analysis results to avoid repeated processing of the same URLs,
    improving performance and reducing load on external services.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 60):
        """
        Initialize the analysis cache.
        
        Args:
            max_size: Maximum number of cached entries
            default_ttl_minutes: Default time-to-live for cache entries in minutes
        """
        self.max_size = max_size
        self.default_ttl_minutes = default_ttl_minutes
        
        # Cache storage: {cache_key: (result, expiry_time, access_time)}
        self._cache: Dict[str, Tuple[AnalysisResponse, float, float]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0
        }
        
        logger.info(f"Analysis cache initialized: max_size={max_size}, ttl={default_ttl_minutes}min")
    
    def _generate_cache_key(self, url: str, analysis_type: str) -> str:
        """
        Generate a cache key for the given URL and analysis type.
        
        Args:
            url: The URL being analyzed
            analysis_type: Type of analysis ('website' or 'github')
            
        Returns:
            SHA-256 hash of the normalized cache key
        """
        # Normalize URL for consistent caching
        normalized_url = url.lower().strip().rstrip('/')
        
        # Create cache key from URL and analysis type
        cache_data = {
            "url": normalized_url,
            "analysis_type": analysis_type
        }
        
        # Generate deterministic hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    async def get(self, url: str, analysis_type: str) -> Optional[AnalysisResponse]:
        """
        Get cached analysis result if available and not expired.
        
        Args:
            url: The URL being analyzed
            analysis_type: Type of analysis ('website' or 'github')
            
        Returns:
            Cached AnalysisResponse if found and valid, None otherwise
        """
        async with self._lock:
            cache_key = self._generate_cache_key(url, analysis_type)
            current_time = time.time()
            
            if cache_key in self._cache:
                result, expiry_time, _ = self._cache[cache_key]
                
                if current_time < expiry_time:
                    # Cache hit - update access time
                    self._cache[cache_key] = (result, expiry_time, current_time)
                    self._stats["hits"] += 1
                    
                    logger.debug(f"Cache hit for {analysis_type} analysis of {url}")
                    return result
                else:
                    # Expired entry - remove it
                    del self._cache[cache_key]
                    self._stats["size"] = len(self._cache)
                    logger.debug(f"Cache entry expired for {analysis_type} analysis of {url}")
            
            # Cache miss
            self._stats["misses"] += 1
            logger.debug(f"Cache miss for {analysis_type} analysis of {url}")
            return None
    
    async def set(self, url: str, analysis_type: str, result: AnalysisResponse, 
                  ttl_minutes: Optional[int] = None) -> None:
        """
        Store analysis result in cache.
        
        Args:
            url: The URL being analyzed
            analysis_type: Type of analysis ('website' or 'github')
            result: Analysis result to cache
            ttl_minutes: Time-to-live in minutes (uses default if None)
        """
        async with self._lock:
            cache_key = self._generate_cache_key(url, analysis_type)
            current_time = time.time()
            
            # Calculate expiry time
            ttl = ttl_minutes if ttl_minutes is not None else self.default_ttl_minutes
            expiry_time = current_time + (ttl * 60)
            
            # Check if we need to evict entries to make space
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                await self._evict_oldest()
            
            # Store the result
            self._cache[cache_key] = (result, expiry_time, current_time)
            self._stats["size"] = len(self._cache)
            
            logger.debug(f"Cached {analysis_type} analysis of {url} (TTL: {ttl}min)")
    
    async def _evict_oldest(self) -> None:
        """
        Evict the oldest accessed cache entry to make space.
        
        Uses LRU (Least Recently Used) eviction policy.
        """
        if not self._cache:
            return
        
        # Find the entry with the oldest access time
        oldest_key = min(self._cache.keys(), 
                        key=lambda k: self._cache[k][2])  # access_time is index 2
        
        del self._cache[oldest_key]
        self._stats["evictions"] += 1
        self._stats["size"] = len(self._cache)
        
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._stats["size"] = 0
            logger.info("Analysis cache cleared")
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for cache_key, (_, expiry_time, _) in self._cache.items():
                if current_time >= expiry_time:
                    expired_keys.append(cache_key)
            
            for key in expired_keys:
                del self._cache[key]
            
            self._stats["size"] = len(self._cache)
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache performance statistics
        """
        async with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_percent": round(hit_rate, 1),
                "evictions": self._stats["evictions"],
                "current_size": self._stats["size"],
                "max_size": self.max_size,
                "utilization_percent": round(self._stats["size"] / self.max_size * 100, 1),
                "default_ttl_minutes": self.default_ttl_minutes
            }
    
    async def get_cache_info(self, url: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific cache entry.
        
        Args:
            url: The URL to check
            analysis_type: Type of analysis
            
        Returns:
            Cache entry information or None if not found
        """
        async with self._lock:
            cache_key = self._generate_cache_key(url, analysis_type)
            current_time = time.time()
            
            if cache_key in self._cache:
                _, expiry_time, access_time = self._cache[cache_key]
                
                return {
                    "cache_key": cache_key,
                    "is_expired": current_time >= expiry_time,
                    "expires_in_seconds": max(0, int(expiry_time - current_time)),
                    "last_accessed": datetime.fromtimestamp(access_time).isoformat(),
                    "expires_at": datetime.fromtimestamp(expiry_time).isoformat()
                }
            
            return None


# Global cache instance
analysis_cache = AnalysisCache(
    max_size=1000,  # Cache up to 1000 analysis results
    default_ttl_minutes=60  # Cache for 1 hour by default
)


async def get_cached_analysis(url: str, analysis_type: str) -> Optional[AnalysisResponse]:
    """
    Convenience function to get cached analysis result.
    
    Args:
        url: The URL being analyzed
        analysis_type: Type of analysis ('website' or 'github')
        
    Returns:
        Cached AnalysisResponse if found and valid, None otherwise
    """
    return await analysis_cache.get(url, analysis_type)


async def cache_analysis_result(url: str, analysis_type: str, result: AnalysisResponse,
                               ttl_minutes: Optional[int] = None) -> None:
    """
    Convenience function to cache analysis result.
    
    Args:
        url: The URL being analyzed
        analysis_type: Type of analysis ('website' or 'github')
        result: Analysis result to cache
        ttl_minutes: Time-to-live in minutes (uses default if None)
    """
    await analysis_cache.set(url, analysis_type, result, ttl_minutes)


async def get_cache_stats() -> Dict[str, Any]:
    """
    Convenience function to get cache statistics.
    
    Returns:
        Dictionary with cache performance statistics
    """
    return await analysis_cache.get_stats()


# Background task for cache maintenance
async def cache_maintenance_task():
    """
    Background task to perform periodic cache maintenance.
    
    This task runs periodically to clean up expired entries and log cache statistics.
    """
    while True:
        try:
            # Clean up expired entries
            expired_count = await analysis_cache.cleanup_expired()
            
            # Log cache statistics every hour
            stats = await analysis_cache.get_stats()
            logger.info(
                f"Cache stats: {stats['hits']} hits, {stats['misses']} misses, "
                f"{stats['hit_rate_percent']}% hit rate, {stats['current_size']}/{stats['max_size']} entries"
            )
            
            # Sleep for 15 minutes before next maintenance
            await asyncio.sleep(15 * 60)
            
        except Exception as e:
            logger.error(f"Error in cache maintenance task: {e}")
            # Sleep for 5 minutes before retrying
            await asyncio.sleep(5 * 60)