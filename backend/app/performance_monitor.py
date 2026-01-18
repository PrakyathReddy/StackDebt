"""
Performance monitoring system for StackDebt API.

Tracks analysis timing, database query performance, and system metrics
to ensure compliance with performance requirements.

Validates: Requirements 8.1, 8.2, 8.5
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Data class for storing performance metrics."""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceStats:
    """Data class for aggregated performance statistics."""
    operation: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p95_duration_ms: float
    success_rate_percent: float


class PerformanceMonitor:
    """
    Performance monitoring system for tracking analysis timing and system metrics.
    
    This monitor tracks operation durations, success rates, and provides
    statistics to ensure compliance with performance requirements.
    """
    
    def __init__(self, max_metrics_per_operation: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            max_metrics_per_operation: Maximum metrics to keep per operation type
        """
        self.max_metrics_per_operation = max_metrics_per_operation
        
        # Storage for metrics: {operation: deque of PerformanceMetric}
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_per_operation))
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Performance requirements (in milliseconds)
        self.requirements = {
            "website_analysis": 10000,  # 10 seconds for website analysis
            "github_analysis": 30000,   # 30 seconds for GitHub analysis (under 100MB)
            "database_query": 1000,     # 1 second for database queries
            "component_detection": 5000, # 5 seconds for component detection
            "age_calculation": 1000     # 1 second for age calculation
        }
        
        logger.info("Performance monitor initialized")
    
    @asynccontextmanager
    async def track_operation(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to track the duration of an operation.
        
        Args:
            operation: Name of the operation being tracked
            metadata: Optional metadata to store with the metric
            
        Usage:
            async with performance_monitor.track_operation("website_analysis"):
                # Perform analysis
                result = await analyze_website(url)
        """
        start_time = time.time()
        success = True
        error = None
        
        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # Add error information to metadata if operation failed
            final_metadata = metadata or {}
            if not success and error:
                final_metadata["error"] = error
            
            await self.record_metric(operation, duration_ms, success, final_metadata)
    
    async def record_metric(self, operation: str, duration_ms: float, success: bool = True,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a performance metric.
        
        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation was successful
            metadata: Optional metadata to store with the metric
        """
        async with self._lock:
            metric = PerformanceMetric(
                operation=operation,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                success=success,
                metadata=metadata or {}
            )
            
            self._metrics[operation].append(metric)
            
            # Check if operation exceeded performance requirements
            if operation in self.requirements:
                requirement_ms = self.requirements[operation]
                if duration_ms > requirement_ms:
                    logger.warning(
                        f"Performance requirement exceeded: {operation} took {duration_ms:.1f}ms "
                        f"(requirement: {requirement_ms}ms)"
                    )
            
            logger.debug(f"Recorded metric: {operation} - {duration_ms:.1f}ms (success: {success})")
    
    async def get_stats(self, operation: Optional[str] = None, 
                       time_window_minutes: Optional[int] = None) -> Dict[str, PerformanceStats]:
        """
        Get performance statistics for operations.
        
        Args:
            operation: Specific operation to get stats for (None for all)
            time_window_minutes: Only include metrics from the last N minutes
            
        Returns:
            Dictionary mapping operation names to PerformanceStats
        """
        async with self._lock:
            stats = {}
            
            operations_to_process = [operation] if operation else self._metrics.keys()
            
            for op in operations_to_process:
                if op not in self._metrics:
                    continue
                
                metrics = list(self._metrics[op])
                
                # Filter by time window if specified
                if time_window_minutes:
                    cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
                    metrics = [m for m in metrics if m.timestamp >= cutoff_time]
                
                if not metrics:
                    continue
                
                # Calculate statistics
                durations = [m.duration_ms for m in metrics]
                successful_metrics = [m for m in metrics if m.success]
                
                # Calculate percentiles
                sorted_durations = sorted(durations)
                p95_index = int(len(sorted_durations) * 0.95)
                p95_duration = sorted_durations[p95_index] if sorted_durations else 0
                
                stats[op] = PerformanceStats(
                    operation=op,
                    total_calls=len(metrics),
                    successful_calls=len(successful_metrics),
                    failed_calls=len(metrics) - len(successful_metrics),
                    avg_duration_ms=sum(durations) / len(durations),
                    min_duration_ms=min(durations),
                    max_duration_ms=max(durations),
                    p95_duration_ms=p95_duration,
                    success_rate_percent=(len(successful_metrics) / len(metrics)) * 100
                )
            
            return stats
    
    async def get_recent_failures(self, operation: Optional[str] = None, 
                                 limit: int = 10) -> List[PerformanceMetric]:
        """
        Get recent failed operations for debugging.
        
        Args:
            operation: Specific operation to get failures for (None for all)
            limit: Maximum number of failures to return
            
        Returns:
            List of recent failed PerformanceMetric objects
        """
        async with self._lock:
            failures = []
            
            operations_to_check = [operation] if operation else self._metrics.keys()
            
            for op in operations_to_check:
                if op not in self._metrics:
                    continue
                
                op_failures = [m for m in self._metrics[op] if not m.success]
                failures.extend(op_failures)
            
            # Sort by timestamp (most recent first) and limit
            failures.sort(key=lambda m: m.timestamp, reverse=True)
            return failures[:limit]
    
    async def check_performance_requirements(self) -> Dict[str, Dict[str, Any]]:
        """
        Check current performance against requirements.
        
        Returns:
            Dictionary with requirement compliance status for each operation
        """
        stats = await self.get_stats(time_window_minutes=60)  # Last hour
        compliance = {}
        
        for operation, requirement_ms in self.requirements.items():
            if operation in stats:
                stat = stats[operation]
                
                # Check various compliance metrics
                avg_compliant = stat.avg_duration_ms <= requirement_ms
                p95_compliant = stat.p95_duration_ms <= requirement_ms * 1.2  # Allow 20% buffer for P95
                success_rate_ok = stat.success_rate_percent >= 95.0  # Require 95% success rate
                
                compliance[operation] = {
                    "requirement_ms": requirement_ms,
                    "avg_duration_ms": stat.avg_duration_ms,
                    "p95_duration_ms": stat.p95_duration_ms,
                    "success_rate_percent": stat.success_rate_percent,
                    "avg_compliant": avg_compliant,
                    "p95_compliant": p95_compliant,
                    "success_rate_ok": success_rate_ok,
                    "overall_compliant": avg_compliant and p95_compliant and success_rate_ok,
                    "total_calls": stat.total_calls
                }
            else:
                compliance[operation] = {
                    "requirement_ms": requirement_ms,
                    "status": "no_data",
                    "overall_compliant": True  # No data means no violations
                }
        
        return compliance
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive performance summary.
        
        Returns:
            Dictionary with overall performance summary
        """
        stats = await self.get_stats(time_window_minutes=60)
        compliance = await self.check_performance_requirements()
        recent_failures = await self.get_recent_failures(limit=5)
        
        # Calculate overall metrics
        total_calls = sum(stat.total_calls for stat in stats.values())
        total_failures = sum(stat.failed_calls for stat in stats.values())
        overall_success_rate = ((total_calls - total_failures) / total_calls * 100) if total_calls > 0 else 100
        
        # Count compliant operations
        compliant_operations = sum(1 for comp in compliance.values() 
                                 if comp.get("overall_compliant", False))
        total_operations_with_requirements = len(self.requirements)
        
        return {
            "summary": {
                "total_operations_tracked": len(stats),
                "total_calls_last_hour": total_calls,
                "overall_success_rate_percent": round(overall_success_rate, 1),
                "compliant_operations": compliant_operations,
                "total_operations_with_requirements": total_operations_with_requirements,
                "compliance_rate_percent": round(compliant_operations / total_operations_with_requirements * 100, 1) if total_operations_with_requirements > 0 else 100
            },
            "operation_stats": {op: {
                "avg_duration_ms": round(stat.avg_duration_ms, 1),
                "p95_duration_ms": round(stat.p95_duration_ms, 1),
                "success_rate_percent": round(stat.success_rate_percent, 1),
                "total_calls": stat.total_calls
            } for op, stat in stats.items()},
            "compliance_status": compliance,
            "recent_failures": [
                {
                    "operation": f.operation,
                    "duration_ms": round(f.duration_ms, 1),
                    "timestamp": f.timestamp.isoformat(),
                    "error": f.metadata.get("error", "Unknown error")
                }
                for f in recent_failures
            ]
        }
    
    async def clear_metrics(self, operation: Optional[str] = None) -> None:
        """
        Clear stored metrics.
        
        Args:
            operation: Specific operation to clear (None for all)
        """
        async with self._lock:
            if operation:
                if operation in self._metrics:
                    self._metrics[operation].clear()
                    logger.info(f"Cleared metrics for operation: {operation}")
            else:
                self._metrics.clear()
                logger.info("Cleared all performance metrics")


# Global performance monitor instance
performance_monitor = PerformanceMonitor(max_metrics_per_operation=1000)


# Convenience functions
async def track_website_analysis(metadata: Optional[Dict[str, Any]] = None):
    """Context manager for tracking website analysis performance."""
    return performance_monitor.track_operation("website_analysis", metadata)


async def track_github_analysis(metadata: Optional[Dict[str, Any]] = None):
    """Context manager for tracking GitHub analysis performance."""
    return performance_monitor.track_operation("github_analysis", metadata)


async def track_database_query(metadata: Optional[Dict[str, Any]] = None):
    """Context manager for tracking database query performance."""
    return performance_monitor.track_operation("database_query", metadata)


async def track_component_detection(metadata: Optional[Dict[str, Any]] = None):
    """Context manager for tracking component detection performance."""
    return performance_monitor.track_operation("component_detection", metadata)


async def track_age_calculation(metadata: Optional[Dict[str, Any]] = None):
    """Context manager for tracking age calculation performance."""
    return performance_monitor.track_operation("age_calculation", metadata)


async def get_performance_stats() -> Dict[str, Any]:
    """Get comprehensive performance statistics."""
    return await performance_monitor.get_performance_summary()


# Background task for performance monitoring
async def performance_monitoring_task():
    """
    Background task to monitor performance and log warnings.
    
    This task runs periodically to check performance requirements
    and log warnings for non-compliant operations.
    """
    while True:
        try:
            compliance = await performance_monitor.check_performance_requirements()
            
            # Log warnings for non-compliant operations
            for operation, status in compliance.items():
                if not status.get("overall_compliant", True) and status.get("total_calls", 0) > 0:
                    logger.warning(
                        f"Performance requirement violation: {operation} - "
                        f"avg: {status.get('avg_duration_ms', 0):.1f}ms, "
                        f"p95: {status.get('p95_duration_ms', 0):.1f}ms, "
                        f"success rate: {status.get('success_rate_percent', 0):.1f}% "
                        f"(requirement: {status['requirement_ms']}ms)"
                    )
            
            # Log overall performance summary every 30 minutes
            summary = await performance_monitor.get_performance_summary()
            logger.info(
                f"Performance summary: {summary['summary']['total_calls_last_hour']} calls, "
                f"{summary['summary']['overall_success_rate_percent']}% success rate, "
                f"{summary['summary']['compliance_rate_percent']}% compliance rate"
            )
            
            # Sleep for 10 minutes before next check
            await asyncio.sleep(10 * 60)
            
        except Exception as e:
            logger.error(f"Error in performance monitoring task: {e}")
            # Sleep for 5 minutes before retrying
            await asyncio.sleep(5 * 60)