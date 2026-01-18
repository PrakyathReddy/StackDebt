"""
Unit tests for HTTP Header Scraper service.

Tests specific server header formats, edge cases, and error handling
for the HTTP Header Scraper service.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import httpx
from app.http_header_scraper import HTTPHeaderScraper
from app.encyclopedia import EncyclopediaRepository
from app.schemas import Component, ComponentCategory, RiskLevel, ComponentDetectionResult
from app.models import VersionRelease


class TestHTTPHeaderScraper:
    """Test suite for HTTPHeaderScraper class."""

    @pytest.fixture
    def mock_encyclopedia(self):
        """Create a mock encyclopedia for testing."""
        encyclopedia = Mock(spec=EncyclopediaRepository)
        return encyclopedia

    @pytest.fixture
    def scraper(self, mock_encyclopedia):
        """Create HTTPHeaderScraper instance with mock encyclopedia."""
        return HTTPHeaderScraper(mock_encyclopedia)

    def test_normalize_url_adds_https_scheme(self, scraper):
        """Test that URLs without scheme get https:// added."""
        result = scraper._normalize_url("example.com")
        assert result == "https://example.com"

    def test_normalize_url_preserves_existing_scheme(self, scraper):
        """Test that URLs with existing scheme are preserved."""
        result = scraper._normalize_url("http://example.com")
        assert result == "http://example.com"

    def test_normalize_url_raises_on_invalid_format(self, scraper):
        """Test that invalid URL formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            scraper._normalize_url("not-a-url")

    def test_parse_server_header_apache(self, scraper):
        """Test parsing Apache server header."""
        headers = {"server": "Apache/2.4.41 (Ubuntu)"}
        result = scraper._parse_server_header(headers)
        
        assert result is not None
        assert result.name == "apache"
        assert result.version == "2.4.41"
        assert result.category == ComponentCategory.WEB_SERVER
        assert result.weight == 0.3

    def test_parse_server_header_nginx(self, scraper):
        """Test parsing nginx server header."""
        headers = {"server": "nginx/1.18.0"}
        result = scraper._parse_server_header(headers)
        
        assert result is not None
        assert result.name == "nginx"
        assert result.version == "1.18.0"
        assert result.category == ComponentCategory.WEB_SERVER

    def test_parse_server_header_iis(self, scraper):
        """Test parsing IIS server header."""
        headers = {"server": "Microsoft-IIS/10.0"}
        result = scraper._parse_server_header(headers)
        
        assert result is not None
        assert result.name == "iis"
        assert result.version == "10.0"
        assert result.category == ComponentCategory.WEB_SERVER

    def test_parse_server_header_cloudflare(self, scraper):
        """Test parsing Cloudflare server header."""
        headers = {"server": "cloudflare"}
        result = scraper._parse_server_header(headers)
        
        assert result is not None
        assert result.name == "cloudflare"
        assert result.version == "unknown"
        assert result.category == ComponentCategory.WEB_SERVER

    def test_parse_server_header_generic(self, scraper):
        """Test parsing generic server header with version."""
        headers = {"server": "CustomServer/1.2.3"}
        result = scraper._parse_server_header(headers)
        
        assert result is not None
        assert result.name == "customserver"
        assert result.version == "1.2.3"
        assert result.category == ComponentCategory.WEB_SERVER

    def test_parse_server_header_no_server(self, scraper):
        """Test parsing when no server header present."""
        headers = {}
        result = scraper._parse_server_header(headers)
        assert result is None

    def test_parse_powered_by_header_php(self, scraper):
        """Test parsing PHP from X-Powered-By header."""
        powered_by = "PHP/7.4.3"
        result = scraper._parse_powered_by_header(powered_by)
        
        assert len(result) == 1
        component = result[0]
        assert component.name == "php"
        assert component.version == "7.4.3"
        assert component.category == ComponentCategory.PROGRAMMING_LANGUAGE
        assert component.weight == 0.7

    def test_parse_powered_by_header_aspnet(self, scraper):
        """Test parsing ASP.NET from X-Powered-By header."""
        powered_by = "ASP.NET"
        result = scraper._parse_powered_by_header(powered_by)
        
        assert len(result) == 1
        component = result[0]
        assert component.name == "asp.net"
        assert component.version == "unknown"
        assert component.category == ComponentCategory.FRAMEWORK

    def test_parse_powered_by_header_express(self, scraper):
        """Test parsing Express from X-Powered-By header."""
        powered_by = "Express"
        result = scraper._parse_powered_by_header(powered_by)
        
        assert len(result) == 1
        component = result[0]
        assert component.name == "express"
        assert component.category == ComponentCategory.FRAMEWORK

    def test_parse_generator_header_wordpress(self, scraper):
        """Test parsing WordPress from X-Generator header."""
        generator = "WordPress 5.8.1"
        result = scraper._parse_generator_header(generator)
        
        assert len(result) == 1
        component = result[0]
        assert component.name == "wordpress"
        assert component.version == "5.8.1"
        assert component.category == ComponentCategory.FRAMEWORK

    def test_parse_generator_header_drupal(self, scraper):
        """Test parsing Drupal from X-Generator header."""
        generator = "Drupal 9"
        result = scraper._parse_generator_header(generator)
        
        assert len(result) == 1
        component = result[0]
        assert component.name == "drupal"
        assert component.version == "9"
        assert component.category == ComponentCategory.FRAMEWORK

    def test_detect_cdn_cloudflare(self, scraper):
        """Test detecting Cloudflare CDN from headers."""
        headers = {"cf-ray": "12345", "cf-cache-status": "HIT"}
        result = scraper._detect_cdn(headers)
        
        assert result is not None
        assert result.name == "cloudflare"
        assert result.category == ComponentCategory.WEB_SERVER
        assert result.weight == 0.1

    def test_detect_cdn_cloudfront(self, scraper):
        """Test detecting CloudFront CDN from server header."""
        headers = {"server": "CloudFront"}
        result = scraper._detect_cdn(headers)
        
        assert result is not None
        assert result.name == "cloudfront"
        assert result.category == ComponentCategory.WEB_SERVER

    def test_detect_cdn_none(self, scraper):
        """Test no CDN detection when no CDN headers present."""
        headers = {"server": "nginx/1.18.0"}
        result = scraper._detect_cdn(headers)
        assert result is None

    def test_detect_technologies_multiple_headers(self, scraper):
        """Test detecting technologies from multiple headers."""
        headers = {
            "x-powered-by": "PHP/7.4.3",
            "x-generator": "WordPress 5.8.1",
            "cf-ray": "12345"
        }
        result = scraper._detect_technologies(headers)
        
        # Should detect PHP, WordPress, and Cloudflare
        assert len(result) == 3
        names = [comp.name for comp in result]
        assert "php" in names
        assert "wordpress" in names
        assert "cloudflare" in names

    def test_calculate_age_years(self, scraper):
        """Test age calculation from release date."""
        # Test with a date 2 years ago
        release_date = date(2022, 1, 1)
        with patch('app.http_header_scraper.date') as mock_date:
            mock_date.today.return_value = date(2024, 1, 1)
            age = scraper._calculate_age_years(release_date)
            assert age == 2.0

    def test_calculate_risk_level_critical_age(self, scraper):
        """Test risk level calculation for old components."""
        risk = scraper._calculate_risk_level(6.0, None)
        assert risk == RiskLevel.CRITICAL

    def test_calculate_risk_level_warning_age(self, scraper):
        """Test risk level calculation for moderately old components."""
        risk = scraper._calculate_risk_level(3.0, None)
        assert risk == RiskLevel.WARNING

    def test_calculate_risk_level_ok_age(self, scraper):
        """Test risk level calculation for new components."""
        risk = scraper._calculate_risk_level(1.0, None)
        assert risk == RiskLevel.OK

    def test_calculate_risk_level_eol_critical(self, scraper):
        """Test risk level calculation for end-of-life components."""
        with patch('app.http_header_scraper.date') as mock_date:
            mock_date.today.return_value = date(2024, 1, 1)
            eol_date = date(2023, 12, 31)  # Past EOL
            risk = scraper._calculate_risk_level(1.0, eol_date)
            assert risk == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_enrich_component_data_found(self, scraper, mock_encyclopedia):
        """Test component enrichment when version is found in encyclopedia."""
        # Setup mock encyclopedia response
        version_info = Mock()
        version_info.release_date = date(2022, 1, 1)
        version_info.end_of_life_date = None
        mock_encyclopedia.lookup_version.return_value = version_info
        
        component = Component(
            name="nginx",
            version="1.18.0",
            release_date=date.today(),
            category=ComponentCategory.WEB_SERVER,
            risk_level=RiskLevel.OK,
            age_years=0.0,
            weight=0.3
        )
        
        with patch('app.http_header_scraper.date') as mock_date:
            mock_date.today.return_value = date(2024, 1, 1)
            result = await scraper._enrich_component_data(component)
        
        assert result.release_date == date(2022, 1, 1)
        assert result.age_years == 2.0
        assert result.risk_level == RiskLevel.WARNING

    @pytest.mark.asyncio
    async def test_enrich_component_data_not_found(self, scraper, mock_encyclopedia):
        """Test component enrichment when version is not found in encyclopedia."""
        mock_encyclopedia.lookup_version.return_value = None
        
        component = Component(
            name="unknown-server",
            version="1.0.0",
            release_date=date.today(),
            category=ComponentCategory.WEB_SERVER,
            risk_level=RiskLevel.OK,
            age_years=0.0,
            weight=0.3
        )
        
        result = await scraper._enrich_component_data(component)
        assert result == component  # Should return unchanged

    @pytest.mark.asyncio
    async def test_enrich_component_data_unknown_version(self, scraper, mock_encyclopedia):
        """Test component enrichment with unknown version."""
        component = Component(
            name="cloudflare",
            version="unknown",
            release_date=date.today(),
            category=ComponentCategory.WEB_SERVER,
            risk_level=RiskLevel.OK,
            age_years=0.0,
            weight=0.1
        )
        
        result = await scraper._enrich_component_data(component)
        assert result == component  # Should return unchanged
        mock_encyclopedia.lookup_version.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_headers_success(self, scraper):
        """Test successful header fetching."""
        mock_response = Mock()
        mock_response.headers = {"Server": "nginx/1.18.0", "X-Powered-By": "PHP/7.4.3"}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.head.return_value = mock_response
            
            headers = await scraper._fetch_headers("https://example.com")
            
            assert headers == {"server": "nginx/1.18.0", "x-powered-by": "PHP/7.4.3"}

    @pytest.mark.asyncio
    async def test_fetch_headers_head_fails_get_succeeds(self, scraper):
        """Test fallback to GET when HEAD request fails."""
        mock_head_response = Mock()
        mock_head_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Method not allowed", request=Mock(), response=Mock()
        )
        
        mock_get_response = Mock()
        mock_get_response.headers = {"Server": "apache/2.4.41"}
        mock_get_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            client_instance = mock_client.return_value.__aenter__.return_value
            client_instance.head.return_value = mock_head_response
            client_instance.get.return_value = mock_get_response
            
            headers = await scraper._fetch_headers("https://example.com")
            
            assert headers == {"server": "apache/2.4.41"}

    @pytest.mark.asyncio
    async def test_analyze_website_success(self, scraper, mock_encyclopedia):
        """Test successful website analysis."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.headers = {
            "Server": "nginx/1.18.0",
            "X-Powered-By": "PHP/7.4.3"
        }
        mock_response.raise_for_status = Mock()
        
        # Mock encyclopedia response
        version_info = Mock()
        version_info.release_date = date(2020, 1, 1)
        version_info.end_of_life_date = None
        mock_encyclopedia.lookup_version.return_value = version_info
        
        with patch('httpx.AsyncClient') as mock_client, \
             patch('app.http_header_scraper.date') as mock_date:
            
            mock_client.return_value.__aenter__.return_value.head.return_value = mock_response
            mock_date.today.return_value = date(2024, 1, 1)
            
            result = await scraper.analyze_website("https://example.com")
            
            assert isinstance(result, ComponentDetectionResult)
            assert len(result.detected_components) == 2  # nginx and php
            assert result.detection_metadata['analysis_type'] == 'website'
            assert 'detection_time_ms' in result.detection_metadata

    @pytest.mark.asyncio
    async def test_analyze_website_timeout_error(self, scraper):
        """Test handling of timeout errors."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.head.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(httpx.RequestError, match="timed out after 10 seconds"):
                await scraper.analyze_website("https://example.com")

    @pytest.mark.asyncio
    async def test_analyze_website_connection_error(self, scraper):
        """Test handling of connection errors."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.head.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(httpx.RequestError, match="website may be unreachable"):
                await scraper.analyze_website("https://example.com")

    @pytest.mark.asyncio
    async def test_analyze_website_forbidden_error(self, scraper):
        """Test handling of 403 Forbidden errors."""
        mock_response = Mock()
        mock_response.status_code = 403
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock both HEAD and GET to raise HTTPStatusError
            mock_client.return_value.__aenter__.return_value.head.side_effect = httpx.HTTPStatusError(
                "Forbidden", request=Mock(), response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "Forbidden", request=Mock(), response=mock_response
            )
            
            with pytest.raises(httpx.RequestError, match="website may be blocking scraping"):
                await scraper.analyze_website("https://example.com")

    @pytest.mark.asyncio
    async def test_analyze_website_404_error(self, scraper):
        """Test handling of 404 Not Found errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock both HEAD and GET to raise HTTPStatusError
            mock_client.return_value.__aenter__.return_value.head.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "Not Found", request=Mock(), response=mock_response
            )
            
            with pytest.raises(httpx.RequestError, match="not found \\(404\\)"):
                await scraper.analyze_website("https://example.com")

    @pytest.mark.asyncio
    async def test_analyze_website_partial_enrichment_failure(self, scraper, mock_encyclopedia):
        """Test handling when some component enrichment fails."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.headers = {
            "Server": "nginx/1.18.0",
            "X-Powered-By": "PHP/7.4.3"
        }
        mock_response.raise_for_status = Mock()
        
        # Mock encyclopedia to fail for one component
        async def mock_lookup_version(name, version):
            if name.lower() == "nginx":
                version_info = Mock()
                version_info.release_date = date(2020, 1, 1)
                version_info.end_of_life_date = None
                return version_info
            else:
                raise Exception("Database error")
        
        mock_encyclopedia.lookup_version.side_effect = mock_lookup_version
        
        with patch('httpx.AsyncClient') as mock_client, \
             patch('app.http_header_scraper.date') as mock_date:
            
            mock_client.return_value.__aenter__.return_value.head.return_value = mock_response
            mock_date.today.return_value = date(2024, 1, 1)
            
            result = await scraper.analyze_website("https://example.com")
            
            # Should have two components - nginx with real date, php with fallback date
            assert len(result.detected_components) == 2
            assert len(result.failed_detections) == 0  # Components are returned with fallback data
            
            # Find the components
            nginx_component = next(c for c in result.detected_components if c.name == 'nginx')
            php_component = next(c for c in result.detected_components if c.name == 'php')
            
            # nginx should have the mocked release date
            assert nginx_component.release_date == date(2020, 1, 1)
            
            # php should have today's date as fallback (since enrichment failed)
            assert php_component.release_date == date(2024, 1, 1)  # mocked today