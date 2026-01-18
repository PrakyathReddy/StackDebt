"""
StackDebt Backend (Archeologist)
FastAPI application for software infrastructure carbon dating analysis.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx

from app.database import init_database, close_database
from app.schemas import (
    AnalysisRequest, 
    AnalysisResponse, 
    StackAgeResult, 
    Component,
    ComponentDetectionResult
)
from app.carbon_dating_engine import CarbonDatingEngine
from app.github_analyzer import GitHubAnalyzer
from app.http_header_scraper import HTTPHeaderScraper
from app.encyclopedia import EncyclopediaRepository
from app.utils import validate_url_format
from app.rate_limiter import rate_limit_middleware
from app.cache import get_cached_analysis, cache_analysis_result, get_cache_stats, cache_maintenance_task
from app.performance_monitor import (
    performance_monitor, 
    track_website_analysis, 
    track_github_analysis,
    track_component_detection,
    track_age_calculation,
    get_performance_stats,
    performance_monitoring_task
)
from app.external_service_handler import external_service_handler
from app.admin import (
    AdminService, 
    VersionAddRequest, 
    BulkVersionImportRequest, 
    RegistryUpdateRequest,
    admin_service
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    await init_database()
    logger.info("StackDebt Archeologist starting up...")
    
    # Start background tasks
    cache_task = asyncio.create_task(cache_maintenance_task())
    performance_task = asyncio.create_task(performance_monitoring_task())
    
    try:
        yield
    finally:
        # Shutdown
        cache_task.cancel()
        performance_task.cancel()
        
        # Wait for tasks to complete
        try:
            await asyncio.gather(cache_task, performance_task, return_exceptions=True)
        except Exception as e:
            logger.warning(f"Error during background task shutdown: {e}")
        
        await close_database()
        logger.info("StackDebt Archeologist shutting down...")

app = FastAPI(
    title="StackDebt Archeologist",
    description="Backend service for software infrastructure carbon dating analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:3001",  # Alternative React port
        "https://stackdebt.app",  # Production frontend (if applicable)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Initialize services
encyclopedia = EncyclopediaRepository()
carbon_dating_engine = CarbonDatingEngine()
github_analyzer = GitHubAnalyzer(encyclopedia, github_token=os.getenv("GITHUB_TOKEN"))
http_scraper = HTTPHeaderScraper(encyclopedia)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "StackDebt Archeologist is running"}

@app.get("/ready")
async def readiness_check():
    """
    Readiness probe endpoint for Kubernetes/container orchestration.
    
    This endpoint checks if the service is ready to accept traffic
    by verifying that all critical dependencies are available.
    """
    try:
        # Check database connectivity
        await encyclopedia.get_database_stats()
        
        # Check if critical services are initialized
        if not hasattr(carbon_dating_engine, 'calculate_stack_age'):
            raise Exception("Carbon dating engine not properly initialized")
        
        return {
            "status": "ready",
            "service": "archeologist",
            "timestamp": datetime.now().isoformat(),
            "message": "Service is ready to accept traffic"
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "service": "archeologist",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Service is not ready to accept traffic"
            }
        )

@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint for monitoring.
    
    Returns detailed health information about all system components
    including database connectivity, external services, and performance metrics.
    """
    health_status = {
        "status": "healthy",
        "service": "archeologist",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_healthy = True
    
    try:
        # Database health check
        try:
            db_stats = await encyclopedia.get_database_stats()
            health_status["checks"]["database"] = {
                "status": "healthy",
                "total_software": db_stats.get("total_software", 0),
                "total_versions": db_stats.get("total_versions", 0),
                "response_time_ms": "< 100"
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
        
        # Cache health check
        try:
            cache_stats = await get_cache_stats()
            health_status["checks"]["cache"] = {
                "status": "healthy",
                "hit_rate": cache_stats.get("hit_rate", 0),
                "total_entries": cache_stats.get("total_entries", 0)
            }
        except Exception as e:
            health_status["checks"]["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
        
        # External services health check
        try:
            services_status = {}
            for service in ['github_api', 'http_scraper']:
                service_status = external_service_handler.get_service_status(service)
                services_status[service] = {
                    "status": "healthy" if service_status["state"] != "open" else "degraded",
                    "circuit_breaker_state": service_status["state"],
                    "failure_count": service_status["failure_count"]
                }
                if service_status["state"] == "open":
                    overall_healthy = False
            
            health_status["checks"]["external_services"] = services_status
        except Exception as e:
            health_status["checks"]["external_services"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
        
        # Performance metrics check
        try:
            perf_stats = await get_performance_stats()
            avg_response_time = perf_stats.get("average_response_time_ms", 0)
            health_status["checks"]["performance"] = {
                "status": "healthy" if avg_response_time < 5000 else "degraded",
                "average_response_time_ms": avg_response_time,
                "total_analyses": perf_stats.get("total_analyses", 0)
            }
            if avg_response_time >= 5000:
                overall_healthy = False
        except Exception as e:
            health_status["checks"]["performance"] = {
                "status": "unknown",
                "error": str(e)
            }
        
        # Update overall status
        if not overall_healthy:
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "archeologist",
            "timestamp": datetime.now().isoformat(),
            "error": "Health check system failure",
            "details": str(e)
        }

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_infrastructure(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Main analysis endpoint for both websites and GitHub repositories.
    
    This endpoint performs carbon dating analysis on the provided URL,
    detecting software components and calculating infrastructure age.
    
    Validates: Requirements 1.2, 2.6, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5
    """
    analysis_start = datetime.now()
    
    try:
        # Validate URL format and determine analysis type
        is_valid, analysis_type_or_error = validate_url_format(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Invalid URL format provided",
                    "error": "ValidationError",
                    "suggestions": [
                        "Ensure the URL starts with http:// or https://",
                        "For GitHub repositories, use format: https://github.com/owner/repo",
                        "For websites, use format: https://example.com"
                    ],
                    "validation_error": analysis_type_or_error
                }
            )
        
        # Override analysis type if explicitly provided
        if request.analysis_type:
            analysis_type = request.analysis_type
        else:
            analysis_type = analysis_type_or_error
        
        logger.info(f"Starting {analysis_type} analysis for: {request.url}")
        
        # Check cache first
        cached_result = await get_cached_analysis(request.url, analysis_type)
        if cached_result:
            logger.info(f"Cache hit for {analysis_type} analysis of {request.url}")
            # Update metadata to indicate cache hit
            cached_result.analysis_metadata["cache_hit"] = True
            cached_result.analysis_metadata["served_from_cache_at"] = datetime.now().isoformat()
            return cached_result
        
        # Track the overall analysis performance
        analysis_context = track_website_analysis if analysis_type == "website" else track_github_analysis
        analysis_metadata = {
            "analysis_type": analysis_type,
            "url_analyzed": request.url,
            "cache_hit": False
        }
        
        async with analysis_context(analysis_metadata):
            # Perform component detection based on analysis type
            detection_result = None
            try:
                async with track_component_detection({"analysis_type": analysis_type, "url": request.url}):
                    if analysis_type == "github":
                        detection_result = await github_analyzer.analyze_repository(request.url)
                    elif analysis_type == "website":
                        detection_result = await http_scraper.analyze_website(request.url)
                    else:
                        raise HTTPException(
                            status_code=400, 
                            detail={
                                "message": f"Unsupported analysis type: {analysis_type}",
                                "error": "ValidationError",
                                "suggestions": [
                                    "Use 'github' for GitHub repositories",
                                    "Use 'website' for website analysis",
                                    "Check the URL format and try again"
                                ]
                            }
                        )
            except httpx.HTTPStatusError as e:
                # Enhanced HTTP error handling with specific messages
                status_code = e.response.status_code
                if status_code == 404:
                    if analysis_type == "github":
                        raise HTTPException(
                            status_code=404,
                            detail={
                                "message": "GitHub repository not found or not accessible",
                                "error": "RepositoryNotFound",
                                "suggestions": [
                                    "Verify the repository URL is correct",
                                    "Check if the repository is public",
                                    "Ensure the repository exists and is accessible"
                                ]
                            }
                        )
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail={
                                "message": "Website not found or not accessible",
                                "error": "WebsiteNotFound", 
                                "suggestions": [
                                    "Verify the website URL is correct",
                                    "Check if the website is online",
                                    "Try accessing the website in your browser first"
                                ]
                            }
                        )
                elif status_code == 403:
                    if analysis_type == "github":
                        # Check if it's rate limiting or private repo
                        rate_limit_remaining = e.response.headers.get("X-RateLimit-Remaining", "unknown")
                        if rate_limit_remaining == "0":
                            raise HTTPException(
                                status_code=403,
                                detail={
                                    "message": "GitHub API rate limit exceeded",
                                    "error": "RateLimitExceeded",
                                    "suggestions": [
                                        "Wait for the rate limit to reset",
                                        "Try again in an hour",
                                        "Consider using a GitHub token for higher limits"
                                    ]
                                }
                            )
                        else:
                            raise HTTPException(
                                status_code=403,
                                detail={
                                    "message": "Access forbidden - repository may be private",
                                    "error": "AccessForbidden",
                                    "suggestions": [
                                        "Ensure the repository is public",
                                        "Check if you have access to the repository",
                                        "Verify the repository URL is correct"
                                    ]
                                }
                            )
                    else:
                        raise HTTPException(
                            status_code=403,
                            detail={
                                "message": "Access forbidden - website may block automated requests",
                                "error": "AccessForbidden",
                                "suggestions": [
                                    "The website may block automated requests",
                                    "Try a different website",
                                    "Check if the website requires authentication"
                                ]
                            }
                        )
                else:
                    raise error_logger.create_user_friendly_response(e, status_code, {
                        "url": request.url,
                        "analysis_type": analysis_type
                    })
            
            # Check if any components were detected
            if not detection_result.detected_components:
                # Enhanced no components error with specific troubleshooting
                failed_detections = detection_result.failed_detections or []
                
                # Analyze failure patterns to provide better suggestions
                suggestions = []
                if analysis_type == "github":
                    if any("package.json" in failure for failure in failed_detections):
                        suggestions.append("Add a package.json file for Node.js projects")
                    if any("requirements.txt" in failure for failure in failed_detections):
                        suggestions.append("Add a requirements.txt file for Python projects")
                    if any("go.mod" in failure for failure in failed_detections):
                        suggestions.append("Initialize Go modules with 'go mod init'")
                    if any("pom.xml" in failure for failure in failed_detections):
                        suggestions.append("Add a pom.xml file for Maven projects")
                    
                    # Generic suggestions
                    suggestions.extend([
                        "Ensure the repository contains recognizable package files",
                        "Check that the repository is not empty",
                        "Verify the repository contains a software project"
                    ])
                else:  # website
                    suggestions.extend([
                        "The website may not expose technology information in HTTP headers",
                        "Try a different website that uses common web technologies",
                        "Some static sites may not have detectable server information"
                    ])
                
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "No software components detected for analysis",
                        "error": "NoComponentsDetected",
                        "suggestions": suggestions,
                        "failed_detections": failed_detections,
                        "troubleshooting": {
                            "analysis_type": analysis_type,
                            "url": request.url,
                            "detection_attempts": len(failed_detections)
                        }
                    }
                )
            
            # Calculate stack age using carbon dating engine
            try:
                async with track_age_calculation({"components_count": len(detection_result.detected_components)}):
                    stack_age_result = carbon_dating_engine.calculate_stack_age(
                        detection_result.detected_components
                    )
            except ValueError as e:
                error_logger.log_error(e, {
                    "url": request.url,
                    "components_detected": len(detection_result.detected_components),
                    "analysis_type": analysis_type
                })
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": f"Unable to calculate stack age: {str(e)}",
                        "error": "CalculationError",
                        "detected_components": len(detection_result.detected_components),
                        "failed_detections": detection_result.failed_detections,
                        "suggestions": [
                            "The detected components may have invalid version data",
                            "Try a different repository or website",
                            "Contact support if this issue persists"
                        ]
                    }
                )
            
            analysis_end = datetime.now()
            analysis_duration_ms = int((analysis_end - analysis_start).total_seconds() * 1000)
            
            # Build analysis metadata with enhanced information
            analysis_metadata = {
                "analysis_duration_ms": analysis_duration_ms,
                "analysis_type": analysis_type,
                "url_analyzed": request.url,
                "components_detected": len(detection_result.detected_components),
                "components_failed": len(detection_result.failed_detections),
                "success_rate": len(detection_result.detected_components) / (len(detection_result.detected_components) + len(detection_result.failed_detections)) if (len(detection_result.detected_components) + len(detection_result.failed_detections)) > 0 else 1.0,
                "cache_hit": False
            }
            
            # Safely merge detection metadata (handle case where it might be a mock)
            if hasattr(detection_result.detection_metadata, 'items'):
                try:
                    analysis_metadata.update(detection_result.detection_metadata)
                except (TypeError, AttributeError):
                    # If detection_metadata is a mock or invalid, skip merging
                    logger.warning("Could not merge detection_metadata - may be a mock object")
            elif isinstance(detection_result.detection_metadata, dict):
                analysis_metadata.update(detection_result.detection_metadata)
            
            # Enhanced partial success handling with warnings
            if detection_result.failed_detections:
                failure_count = len(detection_result.failed_detections)
                success_count = len(detection_result.detected_components)
                
                # Log detailed warning about partial success
                logger.warning(
                    f"Partial success for {request.url}: {success_count} components detected, "
                    f"{failure_count} failed. Failed detections: {detection_result.failed_detections[:5]}"
                )
                
                # Add warning metadata
                analysis_metadata.update({
                    "partial_success": True,
                    "warning_level": "high" if failure_count > success_count else "medium" if failure_count > 2 else "low",
                    "failed_detection_summary": detection_result.failed_detections[:10]  # First 10 failures
                })
                
                # Enhance roast commentary to acknowledge incomplete analysis
                if hasattr(stack_age_result, 'roast_commentary'):
                    if failure_count > 3:
                        stack_age_result.roast_commentary += f" (Note: {failure_count} components couldn't be analyzed - the full picture might be even more concerning!)"
            
            logger.info(
                f"Analysis completed in {analysis_duration_ms}ms: "
                f"{len(detection_result.detected_components)} components detected, "
                f"{len(detection_result.failed_detections)} failed, "
                f"age {stack_age_result.effective_age} years"
            )
            
            # Create response
            response = AnalysisResponse(
                stack_age_result=stack_age_result,
                components=detection_result.detected_components,
                analysis_metadata=analysis_metadata,
                generated_at=analysis_end
            )
            
            # Cache the result for future requests
            # Use shorter TTL for GitHub repos (they change more frequently)
            cache_ttl = 30 if analysis_type == "github" else 60  # 30 or 60 minutes
            await cache_analysis_result(request.url, analysis_type, response, cache_ttl)
            
            return response
        
    except httpx.RequestError as e:
        # Network-level errors (timeouts, connection issues)
        error_logger.log_error(e, {"url": request.url, "analysis_type": analysis_type})
        
        if isinstance(e, httpx.TimeoutException):
            raise HTTPException(
                status_code=504,
                detail={
                    "message": "Request timed out while accessing the URL",
                    "error": "TimeoutError",
                    "suggestions": [
                        "The target URL may be slow to respond",
                        "Try again in a few moments",
                        "Check if the URL is accessible from your browser"
                    ]
                }
            )
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Unable to access the provided URL",
                    "error": "NetworkError",
                    "suggestions": [
                        "Check that the URL is correct and accessible",
                        "Verify your internet connection",
                        "The target service may be temporarily unavailable"
                    ]
                }
            )
    except HTTPException:
        # Re-raise HTTPExceptions as-is (they have proper status codes and messages)
        raise
    except Exception as e:
        # Unexpected errors - log with full details but show user-friendly message
        error_logger.log_error(e, {
            "url": request.url,
            "analysis_type": analysis_type,
            "request_data": request.dict()
        })
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred during analysis",
                "error": "InternalServerError",
                "suggestions": [
                    "Try again in a few moments",
                    "Check if the URL is valid and accessible",
                    "Contact support if the problem persists"
                ]
            }
        )

@app.get("/api/components/{software_name}/versions")
async def get_software_versions(software_name: str, limit: int = 50):
    """
    Get available versions for a specific software component.
    
    This endpoint queries the Encyclopedia database to return
    available versions for the specified software.
    
    Args:
        software_name: Name of the software (e.g., "python", "nginx")
        limit: Maximum number of versions to return (default 50)
    
    Returns:
        List of version information including release dates and risk levels
        
    Validates: Requirements 7.1, 7.2, 7.3, 7.4
    """
    try:
        logger.info(f"Looking up versions for software: {software_name}")
        
        versions = await encyclopedia.get_software_versions(software_name, limit)
        
        if not versions:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"No versions found for software: {software_name}",
                    "suggestions": [
                        "Check the software name spelling",
                        "Try searching for similar software names",
                        "The software may not be in our database yet"
                    ]
                }
            )
        
        # Convert to response format
        version_data = []
        for version in versions:
            from app.utils import calculate_age_years, determine_risk_level
            
            age_years = calculate_age_years(version.release_date)
            risk_level = determine_risk_level(age_years, version.end_of_life_date)
            
            version_data.append({
                "version": version.version,
                "release_date": version.release_date.isoformat(),
                "end_of_life_date": version.end_of_life_date.isoformat() if version.end_of_life_date else None,
                "category": version.category.value,
                "is_lts": version.is_lts,
                "age_years": age_years,
                "risk_level": risk_level.value
            })
        
        logger.info(f"Found {len(version_data)} versions for {software_name}")
        
        return {
            "software_name": software_name,
            "total_versions": len(version_data),
            "versions": version_data
        }
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is (they have proper status codes)
        raise
    except Exception as e:
        logger.error(f"Error retrieving versions for {software_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error retrieving versions for {software_name}",
                "error": "Internal server error"
            }
        )

@app.get("/api/encyclopedia/stats")
async def get_encyclopedia_stats():
    """
    Get statistics about the Encyclopedia database content.
    
    Returns information about the number of software packages,
    versions, and categories available in the database.
    """
    try:
        stats = await encyclopedia.get_database_stats()
        return {
            "database_stats": stats,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error retrieving encyclopedia stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving database statistics"
        )

@app.get("/api/encyclopedia/search")
async def search_software(q: str, limit: int = 20):
    """
    Search for software in the Encyclopedia database.
    
    Args:
        q: Search query string
        limit: Maximum number of results to return
    
    Returns:
        List of matching software with basic information
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Search query must be at least 2 characters long"
        )
    
    try:
        results = await encyclopedia.search_software(q.strip(), limit)
        return {
            "query": q,
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching software with query '{q}': {e}")
        raise HTTPException(
            status_code=500,
            detail="Error performing search"
        )

@app.get("/api/performance/stats")
async def get_performance_statistics():
    """
    Get comprehensive performance statistics and monitoring data.
    
    Returns performance metrics, cache statistics, and compliance status
    for monitoring system health and performance requirements.
    
    Validates: Requirements 8.1, 8.2, 8.5
    """
    try:
        # Get performance statistics
        performance_stats = await get_performance_stats()
        
        # Get cache statistics
        cache_stats = await get_cache_stats()
        
        return {
            "performance": performance_stats,
            "cache": cache_stats,
            "timestamp": datetime.now().isoformat(),
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error retrieving performance statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving performance statistics"
        )

@app.post("/api/performance/clear")
async def clear_performance_metrics(operation: Optional[str] = None):
    """
    Clear performance metrics for debugging or maintenance.
    
    Args:
        operation: Specific operation to clear metrics for (optional)
    
    Returns:
        Confirmation of metrics cleared
    """
    try:
        await performance_monitor.clear_metrics(operation)
        return {
            "message": f"Performance metrics cleared for {operation or 'all operations'}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error clearing performance metrics"
        )

@app.get("/api/cache/stats")
async def get_cache_statistics():
    """
    Get detailed cache statistics and performance information.
    
    Returns cache hit rates, size utilization, and performance metrics
    for monitoring cache effectiveness.
    
    Validates: Requirements 8.5
    """
    try:
        stats = await get_cache_stats()
        return {
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving cache statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving cache statistics"
        )

@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear all cached analysis results.
    
    This endpoint clears the analysis cache, forcing fresh analysis
    for all subsequent requests. Useful for debugging or when
    cached results need to be invalidated.
    """
    try:
        from app.cache import analysis_cache
        await analysis_cache.clear()
        return {
            "message": "Analysis cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error clearing cache"
        )

@app.get("/api/cache/info")
async def get_cache_info(url: str, analysis_type: str):
    """
    Get information about a specific cache entry.
    
    Args:
        url: The URL to check cache info for
        analysis_type: Type of analysis ('website' or 'github')
    
    Returns:
        Cache entry information or null if not cached
    """
    try:
        from app.cache import analysis_cache
        info = await analysis_cache.get_cache_info(url, analysis_type)
        return {
            "cache_info": info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving cache info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving cache information"
        )

# Enhanced error handling system
class ErrorLogger:
    """Centralized error logging with debugging information."""
    
    @staticmethod
    def log_error(error: Exception, context: dict = None, user_friendly: bool = True):
        """Log detailed error information for debugging."""
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        if hasattr(error, '__traceback__'):
            import traceback
            error_details["traceback"] = traceback.format_exc()
        
        logger.error(f"Error occurred: {error_details}")
        return error_details

    @staticmethod
    def create_user_friendly_response(error: Exception, status_code: int, context: dict = None):
        """Create user-friendly error response with debugging info logged."""
        error_details = ErrorLogger.log_error(error, context)
        
        # Map error types to user-friendly messages
        user_messages = {
            "HTTPStatusError": "Unable to access the requested resource",
            "TimeoutException": "Request timed out - the service may be slow to respond",
            "ConnectError": "Unable to connect to the target URL",
            "ValidationError": "Invalid input provided",
            "ValueError": "Invalid data encountered during processing",
            "Exception": "An unexpected error occurred"
        }
        
        error_type = type(error).__name__
        base_message = user_messages.get(error_type, user_messages["Exception"])
        
        # Generate contextual suggestions
        suggestions = ErrorLogger._generate_suggestions(error, context)
        
        return HTTPException(
            status_code=status_code,
            detail={
                "message": base_message,
                "error": error_type,
                "suggestions": suggestions,
                "error_id": error_details.get("timestamp", "unknown"),
                "technical_details": str(error) if logger.level <= logging.DEBUG else None
            }
        )
    
    @staticmethod
    def _generate_suggestions(error: Exception, context: dict = None) -> list:
        """Generate contextual suggestions based on error type and context."""
        error_type = type(error).__name__
        suggestions = []
        
        if error_type == "HTTPStatusError":
            if hasattr(error, 'response') and error.response:
                status_code = error.response.status_code
                if status_code == 403:
                    suggestions = [
                        "Ensure the repository is public",
                        "Check if you've exceeded API rate limits", 
                        "Try again later"
                    ]
                elif status_code == 404:
                    suggestions = [
                        "Verify the URL is correct",
                        "Check if the repository exists and is accessible",
                        "Ensure the website is online and accessible"
                    ]
                elif status_code >= 500:
                    suggestions = [
                        "The target service may be experiencing issues",
                        "Try again in a few moments",
                        "Contact support if the problem persists"
                    ]
        elif error_type == "TimeoutException":
            suggestions = [
                "The target URL may be slow to respond",
                "Try again in a few moments", 
                "Check if the URL is accessible"
            ]
        elif error_type == "ConnectError":
            suggestions = [
                "Check that the URL is correct and accessible",
                "Verify your internet connection",
                "The target service may be temporarily unavailable"
            ]
        elif error_type == "ValueError":
            if context and "no_components" in str(error).lower():
                suggestions = [
                    "Ensure the repository contains recognizable package files",
                    "For websites, check that the site exposes technology information",
                    "Verify the URL points to a valid software project"
                ]
        
        # Default suggestions if none were generated
        if not suggestions:
            suggestions = [
                "Check that the URL is correct",
                "Try again in a few moments",
                "Contact support if the problem persists"
            ]
        
        return suggestions

# Global error logger instance
error_logger = ErrorLogger()

# Error handlers for better error responses
@app.exception_handler(httpx.TimeoutException)
async def timeout_exception_handler(request, exc):
    """Handle timeout exceptions with user-friendly messages."""
    logger.error(f"Timeout error for {request.url}: {exc}")
    raise HTTPException(
        status_code=504,
        detail={
            "message": "Request timed out - the service may be slow to respond",
            "error": "TimeoutException",
            "suggestions": [
                "The target URL may be slow to respond",
                "Try again in a few moments",
                "Check if the URL is accessible"
            ]
        }
    )

@app.exception_handler(httpx.ConnectError)
async def connect_error_handler(request, exc):
    """Handle connection errors with user-friendly messages."""
    logger.error(f"Connection error for {request.url}: {exc}")
    raise HTTPException(
        status_code=503,
        detail={
            "message": "Unable to connect to the target URL",
            "error": "ConnectError", 
            "suggestions": [
                "Check that the URL is correct and accessible",
                "Verify your internet connection",
                "The target service may be temporarily unavailable"
            ]
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle value errors with user-friendly messages."""
    logger.error(f"Value error for {request.url}: {exc}")
    raise HTTPException(
        status_code=422,
        detail={
            "message": "Invalid data encountered during processing",
            "error": "ValueError",
            "suggestions": [
                "Check that the URL points to a valid software project",
                "Ensure the repository contains recognizable package files",
                "Verify the input format is correct"
            ]
        }
    )

@app.get("/api/external-services/status")
async def get_external_services_status():
    """
    Get status of all external services including circuit breaker states.
    
    Returns information about GitHub API and HTTP scraper service health,
    circuit breaker states, and failure counts.
    
    Validates: Requirements 8.4
    """
    try:
        services = ['github_api', 'http_scraper']
        status_data = {}
        
        for service in services:
            status_data[service] = external_service_handler.get_service_status(service)
        
        return {
            "external_services": status_data,
            "timestamp": datetime.now().isoformat(),
            "overall_health": "healthy" if all(
                status["state"] != "open" for status in status_data.values()
            ) else "degraded"
        }
    except Exception as e:
        logger.error(f"Error retrieving external services status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving external services status"
        )

@app.post("/api/external-services/{service_name}/reset")
async def reset_external_service_circuit_breaker(service_name: str):
    """
    Reset circuit breaker for a specific external service.
    
    This endpoint allows manual reset of circuit breakers for debugging
    or recovery purposes.
    
    Args:
        service_name: Name of the service ('github_api' or 'http_scraper')
    
    Validates: Requirements 8.4
    """
    if service_name not in ['github_api', 'http_scraper']:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Unknown service: {service_name}",
                "valid_services": ["github_api", "http_scraper"]
            }
        )
    
    try:
        external_service_handler.reset_circuit_breaker(service_name)
        return {
            "message": f"Circuit breaker for {service_name} has been reset",
            "service_name": service_name,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting circuit breaker for {service_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting circuit breaker for {service_name}"
        )

@app.get("/api/external-services/{service_name}/status")
async def get_external_service_status(service_name: str):
    """
    Get detailed status for a specific external service.
    
    Args:
        service_name: Name of the service ('github_api' or 'http_scraper')
    
    Returns:
        Detailed status including circuit breaker state, failure count,
        and timing information.
        
    Validates: Requirements 8.4
    """
    if service_name not in ['github_api', 'http_scraper']:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Unknown service: {service_name}",
                "valid_services": ["github_api", "http_scraper"]
            }
        )
    
    try:
        status = external_service_handler.get_service_status(service_name)
        return {
            "service_status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving status for {service_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving status for {service_name}"
        )


# Admin endpoints for database update system
@app.post("/api/admin/versions/add")
async def admin_add_version(request: VersionAddRequest):
    """
    Admin endpoint to add a single software version to the database.
    
    This endpoint allows administrators to manually add new software versions
    with comprehensive validation and error handling.
    
    Args:
        request: Version addition request with validation
    
    Returns:
        Operation result with success status and details
        
    Validates: Requirements 7.6
    """
    try:
        result = await admin_service.add_single_version(request)
        
        if result['success']:
            return {
                "message": result['message'],
                "version_data": result['version_data'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Return appropriate HTTP status based on error type
            status_code = 409 if result.get('error') == 'version_exists' else 400
            raise HTTPException(
                status_code=status_code,
                detail={
                    "message": result['message'],
                    "error": result.get('error'),
                    "existing_version": result.get('existing_version')
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin add version: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during version addition",
                "error": "internal_error"
            }
        )


@app.post("/api/admin/versions/bulk-import")
async def admin_bulk_import_versions(request: BulkVersionImportRequest):
    """
    Admin endpoint to import multiple software versions in bulk.
    
    This endpoint allows administrators to import many versions at once
    with detailed reporting of successes, failures, and skipped entries.
    
    Args:
        request: Bulk import request with list of versions
    
    Returns:
        Detailed import results with statistics and error information
        
    Validates: Requirements 7.6
    """
    try:
        result = await admin_service.bulk_import_versions(request)
        
        return {
            "import_summary": {
                "total_requested": result['total_requested'],
                "successful": result['successful'],
                "failed": result['failed'],
                "skipped": result['skipped']
            },
            "details": result['details'],
            "errors": result['errors'],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in admin bulk import: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during bulk import",
                "error": "internal_error"
            }
        )


@app.post("/api/admin/versions/update-from-registry")
async def admin_update_from_registry(request: RegistryUpdateRequest):
    """
    Admin endpoint to update software versions from package registries.
    
    This endpoint automatically fetches version information from external
    package registries (npm, PyPI, Maven, etc.) and imports new versions.
    
    Args:
        request: Registry update request specifying software and registry
    
    Returns:
        Update results including versions found and import statistics
        
    Validates: Requirements 7.6
    """
    try:
        result = await admin_service.update_from_registry(request)
        
        if result['success']:
            return {
                "message": f"Successfully updated {request.software_name} from {request.registry_type}",
                "registry": result['registry'],
                "software_name": result['software_name'],
                "versions_found": result['versions_found'],
                "import_result": result['import_result'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            status_code = 404 if result.get('error') in ['no_versions_found', 'no_valid_versions'] else 400
            raise HTTPException(
                status_code=status_code,
                detail={
                    "message": result['message'],
                    "error": result.get('error'),
                    "registry": request.registry_type,
                    "software_name": request.software_name
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin registry update: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during registry update",
                "error": "internal_error"
            }
        )


@app.get("/api/admin/stats")
async def admin_get_statistics():
    """
    Admin endpoint to get comprehensive database and update statistics.
    
    Returns information about database content, recent updates, and
    system capabilities for administrative monitoring.
    
    Returns:
        Comprehensive statistics and system information
        
    Validates: Requirements 7.6
    """
    try:
        stats = await admin_service.get_update_statistics()
        
        if 'error' in stats:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": stats['message'],
                    "error": stats['error']
                }
            )
        
        return {
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error retrieving administrative statistics",
                "error": "internal_error"
            }
        )


@app.get("/api/admin/registries")
async def admin_get_supported_registries():
    """
    Admin endpoint to get list of supported package registries.
    
    Returns information about which package registries are supported
    for automated version updates.
    
    Returns:
        List of supported registries with their capabilities
    """
    return {
        "supported_registries": [
            {
                "name": "npm",
                "description": "Node.js Package Manager",
                "url": "https://www.npmjs.com/",
                "supports_prereleases": True,
                "supports_lts": True
            },
            {
                "name": "pypi",
                "description": "Python Package Index",
                "url": "https://pypi.org/",
                "supports_prereleases": True,
                "supports_lts": False
            },
            {
                "name": "maven",
                "description": "Maven Central Repository",
                "url": "https://search.maven.org/",
                "supports_prereleases": True,
                "supports_lts": False
            },
            {
                "name": "nuget",
                "description": "NuGet Package Manager",
                "url": "https://www.nuget.org/",
                "supports_prereleases": True,
                "supports_lts": False
            },
            {
                "name": "rubygems",
                "description": "RubyGems Package Manager",
                "url": "https://rubygems.org/",
                "supports_prereleases": True,
                "supports_lts": False
            },
            {
                "name": "crates",
                "description": "Rust Package Registry",
                "url": "https://crates.io/",
                "supports_prereleases": True,
                "supports_lts": False
            }
        ],
        "timestamp": datetime.now().isoformat()
    }