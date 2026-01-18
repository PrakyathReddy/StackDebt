"""
HTTP Header Scraper service for detecting web technologies from HTTP headers.

This service analyzes website HTTP headers to detect publicly visible technologies
such as web servers, CDNs, frontend frameworks, and other exposed components.
It follows Requirements 2.1, 2.2, 8.1, and 9.2.
"""

import asyncio
import re
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse

import httpx
from app.schemas import Component, ComponentCategory, RiskLevel, ComponentDetectionResult
from app.encyclopedia import EncyclopediaRepository
from app.external_service_handler import (
    external_service_handler, 
    RetryableError, 
    NonRetryableError, 
    CircuitBreakerOpenError,
    create_fallback_response
)


class HTTPHeaderScraper:
    """
    Service for scraping HTTP headers to detect web technologies.
    
    This class implements async HTTP requests to analyze website headers
    and detect publicly visible technologies like web servers, CDNs,
    and frontend frameworks.
    """
    
    def __init__(self, encyclopedia: EncyclopediaRepository):
        """Initialize the scraper with encyclopedia for version lookups."""
        self.encyclopedia = encyclopedia
        self.timeout = httpx.Timeout(10.0)  # 10 second timeout per requirement 8.1
        
        # Common server patterns for detection
        self.server_patterns = {
            'apache': re.compile(r'Apache/(\d+\.\d+\.\d+)', re.IGNORECASE),
            'nginx': re.compile(r'nginx/(\d+\.\d+\.\d+)', re.IGNORECASE),
            'iis': re.compile(r'Microsoft-IIS/(\d+\.\d+)', re.IGNORECASE),
            'cloudflare': re.compile(r'cloudflare', re.IGNORECASE),
            'lighttpd': re.compile(r'lighttpd/(\d+\.\d+\.\d+)', re.IGNORECASE),
            'caddy': re.compile(r'Caddy', re.IGNORECASE),
        }
        
        # Technology detection patterns for various headers
        self.tech_patterns = {
            'x-powered-by': {
                'php': re.compile(r'PHP/(\d+\.\d+\.\d+)', re.IGNORECASE),
                'asp.net': re.compile(r'ASP\.NET', re.IGNORECASE),
                'express': re.compile(r'Express', re.IGNORECASE),
                'next.js': re.compile(r'Next\.js', re.IGNORECASE),
            },
            'x-generator': {
                'wordpress': re.compile(r'WordPress (\d+\.\d+\.\d+)', re.IGNORECASE),
                'drupal': re.compile(r'Drupal (\d+)', re.IGNORECASE),
            },
            'x-framework': {
                'laravel': re.compile(r'Laravel', re.IGNORECASE),
                'django': re.compile(r'Django', re.IGNORECASE),
            }
        }

    async def analyze_website(self, url: str) -> ComponentDetectionResult:
        """
        Analyze a website URL to detect technologies from HTTP headers.
        
        Args:
            url: The website URL to analyze
            
        Returns:
            ComponentDetectionResult with detected components and metadata
            
        Raises:
            httpx.RequestError: For network-related errors
            httpx.HTTPStatusError: For HTTP error responses
        """
        detection_start = datetime.now()
        
        async def _perform_analysis():
            detected_components = []
            failed_detections = []
            
            try:
                # Normalize URL
                normalized_url = self._normalize_url(url)
                
                # Make HTTP request with proper headers to avoid blocking
                headers = await self._fetch_headers(normalized_url)
                
                # Parse server information
                server_component = self._parse_server_header(headers)
                if server_component:
                    detected_components.append(server_component)
                
                # Detect additional technologies from various headers
                tech_components = self._detect_technologies(headers)
                detected_components.extend(tech_components)
                
                # Enrich components with version data from encyclopedia
                enriched_components = []
                for component in detected_components:
                    try:
                        enriched = await self._enrich_component_data(component)
                        enriched_components.append(enriched)
                    except Exception as e:
                        failed_detections.append(f"{component.name}@{component.version}: {str(e)}")
                
                detection_end = datetime.now()
                detection_time_ms = int((detection_end - detection_start).total_seconds() * 1000)
                
                return ComponentDetectionResult(
                    detected_components=enriched_components,
                    failed_detections=failed_detections,
                    detection_metadata={
                        'url_analyzed': normalized_url,
                        'headers_found': len(headers),
                        'detection_time_ms': detection_time_ms,
                        'analysis_type': 'website'
                    }
                )
                
            except httpx.TimeoutException:
                raise httpx.RequestError(f"Request to {url} timed out after 10 seconds")
            except httpx.ConnectError:
                raise httpx.RequestError(f"Could not connect to {url} - website may be unreachable")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    raise httpx.RequestError(f"Access forbidden to {url} - website may be blocking scraping")
                elif e.response.status_code == 404:
                    raise httpx.RequestError(f"Website {url} not found (404)")
                else:
                    raise httpx.RequestError(f"HTTP error {e.response.status_code} when accessing {url}")
        
        try:
            # Execute with retry logic and circuit breaker
            return await external_service_handler.execute_with_retry(
                service_name='http_scraper',
                operation=_perform_analysis
            )
            
        except CircuitBreakerOpenError as e:
            # Circuit breaker is open, create fallback response
            fallback_data = create_fallback_response('http_scraper', e, {'url_analyzed': url})
            return ComponentDetectionResult(
                detected_components=[],
                failed_detections=[f"HTTP scraper circuit breaker open: {e}"],
                detection_metadata=fallback_data['detection_metadata']
            )
            
        except (RetryableError, NonRetryableError) as e:
            # All retries exhausted or non-retryable error, create fallback response
            fallback_data = create_fallback_response('http_scraper', e, {'url_analyzed': url})
            return ComponentDetectionResult(
                detected_components=[],
                failed_detections=[f"HTTP scraper failure: {e}"],
                detection_metadata=fallback_data['detection_metadata']
            )
            
        except Exception as e:
            # Unexpected error, still try to provide fallback
            fallback_data = create_fallback_response('http_scraper', e, {'url_analyzed': url})
            return ComponentDetectionResult(
                detected_components=[],
                failed_detections=[f"Unexpected HTTP scraper error: {e}"],
                detection_metadata=fallback_data['detection_metadata']
            )

    async def _fetch_headers(self, url: str) -> Dict[str, str]:
        """
        Fetch HTTP headers from the given URL.
        
        Args:
            url: The URL to fetch headers from
            
        Returns:
            Dictionary of HTTP headers (lowercase keys)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Use HEAD request first to minimize data transfer
            try:
                response = await client.head(
                    url,
                    headers={
                        'User-Agent': 'StackDebt-Analyzer/1.0 (Infrastructure Analysis Tool)',
                        'Accept': '*/*',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    },
                    follow_redirects=True
                )
                response.raise_for_status()
                return {k.lower(): v for k, v in response.headers.items()}
                
            except httpx.HTTPStatusError:
                # If HEAD fails, try GET request
                response = await client.get(
                    url,
                    headers={
                        'User-Agent': 'StackDebt-Analyzer/1.0 (Infrastructure Analysis Tool)',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    },
                    follow_redirects=True
                )
                response.raise_for_status()
                return {k.lower(): v for k, v in response.headers.items()}

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to ensure it has proper scheme and format.
        
        Args:
            url: The URL to normalize
            
        Returns:
            Normalized URL string
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        if not parsed.netloc or '.' not in parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")
        
        return url

    def _parse_server_header(self, headers: Dict[str, str]) -> Optional[Component]:
        """
        Parse the Server header to detect web server information.
        
        Args:
            headers: Dictionary of HTTP headers
            
        Returns:
            Component object if server detected, None otherwise
        """
        server_header = headers.get('server', '')
        if not server_header:
            return None
        
        # Try to match known server patterns
        for server_name, pattern in self.server_patterns.items():
            match = pattern.search(server_header)
            if match:
                if server_name in ['apache', 'nginx', 'lighttpd']:
                    version = match.group(1)
                elif server_name == 'iis':
                    version = match.group(1)
                else:
                    # For servers without version info (cloudflare, caddy)
                    version = 'unknown'
                
                return Component(
                    name=server_name,
                    version=version,
                    release_date=date.today(),  # Will be updated by encyclopedia lookup
                    category=ComponentCategory.WEB_SERVER,
                    risk_level=RiskLevel.OK,  # Will be calculated later
                    age_years=0.0,  # Will be calculated later
                    weight=0.3  # Important component weight
                )
        
        # If no specific pattern matched, try to extract generic server info
        server_parts = server_header.split()[0].split('/')
        if len(server_parts) >= 2:
            name = server_parts[0].lower()
            version = server_parts[1]
            
            return Component(
                name=name,
                version=version,
                release_date=date.today(),
                category=ComponentCategory.WEB_SERVER,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.3
            )
        
        return None

    def _detect_technologies(self, headers: Dict[str, str]) -> List[Component]:
        """
        Detect additional technologies from various HTTP headers.
        
        Args:
            headers: Dictionary of HTTP headers
            
        Returns:
            List of detected Component objects
        """
        components = []
        
        # Check X-Powered-By header
        powered_by = headers.get('x-powered-by', '')
        if powered_by:
            components.extend(self._parse_powered_by_header(powered_by))
        
        # Check X-Generator header
        generator = headers.get('x-generator', '')
        if generator:
            components.extend(self._parse_generator_header(generator))
        
        # Check X-Framework header
        framework = headers.get('x-framework', '')
        if framework:
            components.extend(self._parse_framework_header(framework))
        
        # Check for CDN indicators
        cdn_component = self._detect_cdn(headers)
        if cdn_component:
            components.append(cdn_component)
        
        return components

    def _parse_powered_by_header(self, powered_by: str) -> List[Component]:
        """Parse X-Powered-By header for technology detection."""
        components = []
        
        for tech_name, pattern in self.tech_patterns['x-powered-by'].items():
            match = pattern.search(powered_by)
            if match:
                if tech_name == 'php':
                    version = match.group(1)
                    category = ComponentCategory.PROGRAMMING_LANGUAGE
                    weight = 0.7  # Critical component
                elif tech_name == 'asp.net':
                    version = 'unknown'  # ASP.NET version not always in header
                    category = ComponentCategory.FRAMEWORK
                    weight = 0.3
                elif tech_name in ['express', 'next.js']:
                    version = 'unknown'  # Version not always available
                    category = ComponentCategory.FRAMEWORK
                    weight = 0.3
                else:
                    version = 'unknown'
                    category = ComponentCategory.FRAMEWORK
                    weight = 0.1
                
                components.append(Component(
                    name=tech_name,
                    version=version,
                    release_date=date.today(),
                    category=category,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=weight
                ))
        
        return components

    def _parse_generator_header(self, generator: str) -> List[Component]:
        """Parse X-Generator header for CMS detection."""
        components = []
        
        for tech_name, pattern in self.tech_patterns['x-generator'].items():
            match = pattern.search(generator)
            if match:
                if tech_name in ['wordpress', 'drupal']:
                    version = match.group(1) if match.groups() else 'unknown'
                    category = ComponentCategory.FRAMEWORK
                    weight = 0.3
                else:
                    version = 'unknown'
                    category = ComponentCategory.FRAMEWORK
                    weight = 0.1
                
                components.append(Component(
                    name=tech_name,
                    version=version,
                    release_date=date.today(),
                    category=category,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=weight
                ))
        
        return components

    def _parse_framework_header(self, framework: str) -> List[Component]:
        """Parse X-Framework header for framework detection."""
        components = []
        
        for tech_name, pattern in self.tech_patterns['x-framework'].items():
            match = pattern.search(framework)
            if match:
                components.append(Component(
                    name=tech_name,
                    version='unknown',
                    release_date=date.today(),
                    category=ComponentCategory.FRAMEWORK,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=0.3
                ))
        
        return components

    def _detect_cdn(self, headers: Dict[str, str]) -> Optional[Component]:
        """
        Detect CDN usage from various headers.
        
        Args:
            headers: Dictionary of HTTP headers
            
        Returns:
            Component object if CDN detected, None otherwise
        """
        # Check for Cloudflare
        if any(header.startswith('cf-') for header in headers.keys()):
            return Component(
                name='cloudflare',
                version='unknown',
                release_date=date.today(),
                category=ComponentCategory.WEB_SERVER,  # CDN as web server category
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.1  # Low weight for CDN
            )
        
        # Check for other CDNs via server header
        server = headers.get('server', '').lower()
        if 'cloudfront' in server:
            return Component(
                name='cloudfront',
                version='unknown',
                release_date=date.today(),
                category=ComponentCategory.WEB_SERVER,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.1
            )
        
        return None

    async def _enrich_component_data(self, component: Component) -> Component:
        """
        Enrich component data with version information from encyclopedia.
        
        Args:
            component: Component to enrich
            
        Returns:
            Enriched component with proper release date and risk level
        """
        if component.version == 'unknown':
            # Can't enrich without version info
            return component
        
        try:
            # Look up version in encyclopedia
            version_info = await self.encyclopedia.lookup_version(
                component.name, 
                component.version
            )
            
            if version_info:
                # Calculate age and risk level
                age_years = self._calculate_age_years(version_info.release_date)
                risk_level = self._calculate_risk_level(age_years, version_info.end_of_life_date)
                
                return Component(
                    name=component.name,
                    version=component.version,
                    release_date=version_info.release_date,
                    end_of_life_date=version_info.end_of_life_date,
                    category=component.category,
                    risk_level=risk_level,
                    age_years=age_years,
                    weight=component.weight
                )
            else:
                # Version not found in encyclopedia, return as-is
                return component
                
        except Exception:
            # If enrichment fails, return original component
            return component

    def _calculate_age_years(self, release_date: date) -> float:
        """Calculate age in years from release date."""
        today = date.today()
        age_days = (today - release_date).days
        return round(age_days / 365.25, 1)

    def _calculate_risk_level(self, age_years: float, end_of_life_date: Optional[date]) -> RiskLevel:
        """
        Calculate risk level based on age and EOL status.
        
        Args:
            age_years: Age of component in years
            end_of_life_date: End of life date if known
            
        Returns:
            RiskLevel enum value
        """
        # Check if past end of life
        if end_of_life_date and date.today() > end_of_life_date:
            return RiskLevel.CRITICAL
        
        # Age-based risk classification
        if age_years > 5.0:
            return RiskLevel.CRITICAL
        elif age_years >= 2.0:
            return RiskLevel.WARNING
        else:
            return RiskLevel.OK