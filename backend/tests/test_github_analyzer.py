"""
Unit tests for GitHub Analyzer service.

Tests specific package file parsing functionality and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from app.github_analyzer import GitHubAnalyzer
from app.encyclopedia import EncyclopediaRepository
from app.schemas import Component, ComponentCategory, RiskLevel


class TestGitHubAnalyzer:
    """Test cases for GitHub Analyzer service."""

    @pytest.fixture
    def mock_encyclopedia(self):
        """Create a mock encyclopedia repository."""
        return AsyncMock(spec=EncyclopediaRepository)

    @pytest.fixture
    def analyzer(self, mock_encyclopedia):
        """Create a GitHub analyzer instance with mock encyclopedia."""
        return GitHubAnalyzer(mock_encyclopedia)

    def test_parse_github_url_valid(self, analyzer):
        """Test parsing valid GitHub URLs."""
        owner, repo = analyzer._parse_github_url("https://github.com/user/repo")
        assert owner == "user"
        assert repo == "repo"

    def test_parse_github_url_with_git_suffix(self, analyzer):
        """Test parsing GitHub URLs with .git suffix."""
        owner, repo = analyzer._parse_github_url("https://github.com/user/repo.git")
        assert owner == "user"
        assert repo == "repo"

    def test_parse_github_url_invalid_domain(self, analyzer):
        """Test parsing non-GitHub URLs raises ValueError."""
        with pytest.raises(ValueError, match="Not a GitHub repository URL"):
            analyzer._parse_github_url("https://gitlab.com/user/repo")

    def test_parse_github_url_invalid_format(self, analyzer):
        """Test parsing malformed GitHub URLs raises ValueError."""
        with pytest.raises(ValueError, match="Invalid GitHub repository URL format"):
            analyzer._parse_github_url("https://github.com/user")

    @pytest.mark.asyncio
    async def test_parse_package_json_basic(self, analyzer):
        """Test parsing basic package.json file."""
        content = '''
        {
            "name": "test-app",
            "version": "1.0.0",
            "dependencies": {
                "react": "^18.2.0",
                "express": "~4.18.0"
            },
            "devDependencies": {
                "jest": "29.0.0"
            },
            "engines": {
                "node": "18.17.0"
            }
        }
        '''
        
        components = await analyzer._parse_package_json(content, "package.json")
        
        # Should detect Node.js engine and dependencies
        component_names = [c.name for c in components]
        assert "node.js" in component_names
        assert "react" in component_names
        assert "express" in component_names
        assert "jest" in component_names
        
        # Check Node.js version
        node_component = next(c for c in components if c.name == "node.js")
        assert node_component.version == "18.17.0"
        assert node_component.category == ComponentCategory.PROGRAMMING_LANGUAGE

    @pytest.mark.asyncio
    async def test_parse_package_json_invalid_json(self, analyzer):
        """Test parsing invalid JSON returns empty list."""
        content = '{ invalid json'
        components = await analyzer._parse_package_json(content, "package.json")
        assert components == []

    @pytest.mark.asyncio
    async def test_parse_requirements_txt(self, analyzer):
        """Test parsing requirements.txt file."""
        content = '''
        Django==4.2.0
        requests>=2.28.0
        psycopg2-binary==2.9.5
        # This is a comment
        redis==4.5.0
        '''
        
        components = await analyzer._parse_requirements_txt(content, "requirements.txt")
        
        component_names = [c.name for c in components]
        assert "Django" in component_names
        assert "requests" in component_names
        assert "psycopg2-binary" in component_names
        assert "redis" in component_names
        
        # Check version extraction
        django_component = next(c for c in components if c.name == "Django")
        assert django_component.version == "4.2.0"

    @pytest.mark.asyncio
    async def test_parse_go_mod(self, analyzer):
        """Test parsing go.mod file."""
        content = '''
        module example.com/myapp

        go 1.19

        require (
            github.com/gin-gonic/gin v1.9.0
            github.com/lib/pq v1.10.7
        )
        '''
        
        components = await analyzer._parse_go_mod(content, "go.mod")
        
        component_names = [c.name for c in components]
        assert "go" in component_names
        assert "github.com/gin-gonic/gin" in component_names
        assert "github.com/lib/pq" in component_names
        
        # Check Go version
        go_component = next(c for c in components if c.name == "go")
        assert go_component.version == "1.19"
        assert go_component.category == ComponentCategory.PROGRAMMING_LANGUAGE

    @pytest.mark.asyncio
    async def test_parse_pom_xml(self, analyzer):
        """Test parsing pom.xml file."""
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>myapp</artifactId>
    <version>1.0.0</version>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-core</artifactId>
            <version>5.3.21</version>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
        </dependency>
    </dependencies>
</project>'''
        
        components = await analyzer._parse_pom_xml(content, "pom.xml")
        
        component_names = [c.name for c in components]
        assert "java" in component_names
        assert "org.springframework:spring-core" in component_names
        assert "junit:junit" in component_names
        
        # Check Java version
        java_component = next(c for c in components if c.name == "java")
        assert java_component.version == "11"

    @pytest.mark.asyncio
    async def test_parse_dockerfile(self, analyzer):
        """Test parsing Dockerfile."""
        content = '''
        FROM python:3.9-slim
        
        RUN apt-get update && apt-get install -y \\
            curl \\
            git \\
            && rm -rf /var/lib/apt/lists/*
        
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        '''
        
        components = await analyzer._parse_dockerfile(content, "Dockerfile")
        
        component_names = [c.name for c in components]
        assert "python" in component_names
        assert "curl" in component_names
        assert "git" in component_names
        
        # Check Python base image
        python_component = next(c for c in components if c.name == "python")
        assert python_component.version == "3.9-slim"

    @pytest.mark.asyncio
    async def test_parse_docker_compose(self, analyzer):
        """Test parsing docker-compose.yml file."""
        content = '''
        version: '3.8'
        services:
          web:
            image: nginx:1.21-alpine
            ports:
              - "80:80"
          db:
            image: postgres:13.7
            environment:
              POSTGRES_DB: myapp
          redis:
            image: redis:7.0
        '''
        
        components = await analyzer._parse_docker_compose(content, "docker-compose.yml")
        
        component_names = [c.name for c in components]
        assert "nginx" in component_names
        assert "postgres" in component_names
        assert "redis" in component_names
        
        # Check versions
        nginx_component = next(c for c in components if c.name == "nginx")
        assert nginx_component.version == "1.21-alpine"

    @pytest.mark.asyncio
    async def test_parse_nvmrc(self, analyzer):
        """Test parsing .nvmrc file."""
        content = "v18.17.0"
        components = await analyzer._parse_nvmrc(content, ".nvmrc")
        
        assert len(components) == 1
        assert components[0].name == "node.js"
        assert components[0].version == "18.17.0"
        assert components[0].category == ComponentCategory.PROGRAMMING_LANGUAGE

    @pytest.mark.asyncio
    async def test_parse_python_version(self, analyzer):
        """Test parsing .python-version file."""
        content = "3.9.16"
        components = await analyzer._parse_python_version(content, ".python-version")
        
        assert len(components) == 1
        assert components[0].name == "python"
        assert components[0].version == "3.9.16"
        assert components[0].category == ComponentCategory.PROGRAMMING_LANGUAGE

    def test_extract_version_from_spec(self, analyzer):
        """Test version extraction from various specification formats."""
        assert analyzer._extract_version_from_spec("^18.2.0") == "18.2.0"
        assert analyzer._extract_version_from_spec("~4.18.0") == "4.18.0"
        assert analyzer._extract_version_from_spec(">=2.28.0") == "2.28.0"
        assert analyzer._extract_version_from_spec("1.9.0") == "1.9.0"
        assert analyzer._extract_version_from_spec("v1.9.0") == "1.9.0"
        assert analyzer._extract_version_from_spec("") is None

    def test_categorize_npm_package(self, analyzer):
        """Test npm package categorization."""
        assert analyzer._categorize_npm_package("react") == ComponentCategory.FRAMEWORK
        assert analyzer._categorize_npm_package("express") == ComponentCategory.FRAMEWORK
        assert analyzer._categorize_npm_package("mongodb") == ComponentCategory.DATABASE
        assert analyzer._categorize_npm_package("lodash") == ComponentCategory.LIBRARY

    def test_categorize_python_package(self, analyzer):
        """Test Python package categorization."""
        assert analyzer._categorize_python_package("django") == ComponentCategory.FRAMEWORK
        assert analyzer._categorize_python_package("flask") == ComponentCategory.FRAMEWORK
        assert analyzer._categorize_python_package("psycopg2") == ComponentCategory.DATABASE
        assert analyzer._categorize_python_package("requests") == ComponentCategory.LIBRARY

    def test_categorize_docker_image(self, analyzer):
        """Test Docker image categorization."""
        assert analyzer._categorize_docker_image("ubuntu") == ComponentCategory.OPERATING_SYSTEM
        assert analyzer._categorize_docker_image("python") == ComponentCategory.PROGRAMMING_LANGUAGE
        assert analyzer._categorize_docker_image("postgres") == ComponentCategory.DATABASE
        assert analyzer._categorize_docker_image("nginx") == ComponentCategory.WEB_SERVER
        assert analyzer._categorize_docker_image("myapp") == ComponentCategory.LIBRARY

    def test_extract_apt_packages(self, analyzer):
        """Test APT package extraction from RUN commands."""
        command = "apt-get update && apt-get install -y curl git vim"
        packages = analyzer._extract_apt_packages(command)
        assert "curl" in packages
        assert "git" in packages
        assert "vim" in packages

    def test_extract_yum_packages(self, analyzer):
        """Test YUM package extraction from RUN commands."""
        command = "yum install -y curl git vim"
        packages = analyzer._extract_yum_packages(command)
        assert "curl" in packages
        assert "git" in packages
        assert "vim" in packages

    def test_deduplicate_components(self, analyzer):
        """Test component deduplication."""
        components = [
            Component(
                name="react",
                version="18.2.0",
                release_date=date.today(),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.3
            ),
            Component(
                name="react",
                version="18.2.0",
                release_date=date.today(),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.3
            ),
            Component(
                name="express",
                version="4.18.0",
                release_date=date.today(),
                category=ComponentCategory.FRAMEWORK,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=0.3
            )
        ]
        
        unique_components = analyzer._deduplicate_components(components)
        assert len(unique_components) == 2
        
        names = [c.name for c in unique_components]
        assert "react" in names
        assert "express" in names

    @pytest.mark.asyncio
    async def test_analyze_repository_invalid_url(self, analyzer):
        """Test analyzing repository with invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Not a GitHub repository URL"):
            await analyzer.analyze_repository("https://gitlab.com/user/repo")

    @pytest.mark.asyncio
    async def test_enrich_component_data_with_encyclopedia(self, analyzer, mock_encyclopedia):
        """Test component enrichment with encyclopedia data."""
        from app.models import VersionRelease, ComponentCategory as ModelCategory
        
        # Mock encyclopedia response
        mock_version = VersionRelease(
            id=1,
            software_name="react",
            version="18.2.0",
            release_date=date(2022, 6, 14),
            end_of_life_date=None,
            category=ModelCategory.FRAMEWORK,
            is_lts=False
        )
        mock_encyclopedia.lookup_version.return_value = mock_version
        
        component = Component(
            name="react",
            version="18.2.0",
            release_date=date.today(),
            category=ComponentCategory.FRAMEWORK,
            risk_level=RiskLevel.OK,
            age_years=0.0,
            weight=0.3
        )
        
        enriched = await analyzer._enrich_component_data(component)
        
        assert enriched.release_date == date(2022, 6, 14)
        assert enriched.age_years > 0  # Should be calculated
        mock_encyclopedia.lookup_version.assert_called_once_with("react", "18.2.0")

    @pytest.mark.asyncio
    async def test_enrich_component_data_unknown_version(self, analyzer, mock_encyclopedia):
        """Test component enrichment with unknown version returns unchanged."""
        component = Component(
            name="unknown-package",
            version="unknown",
            release_date=date.today(),
            category=ComponentCategory.LIBRARY,
            risk_level=RiskLevel.OK,
            age_years=0.0,
            weight=0.1
        )
        
        enriched = await analyzer._enrich_component_data(component)
        
        assert enriched == component
        mock_encyclopedia.lookup_version.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_component_data_not_found(self, analyzer, mock_encyclopedia):
        """Test component enrichment when version not found in encyclopedia."""
        mock_encyclopedia.lookup_version.return_value = None
        
        component = Component(
            name="unknown-package",
            version="1.0.0",
            release_date=date.today(),
            category=ComponentCategory.LIBRARY,
            risk_level=RiskLevel.OK,
            age_years=0.0,
            weight=0.1
        )
        
        enriched = await analyzer._enrich_component_data(component)
        
        assert enriched == component
        mock_encyclopedia.lookup_version.assert_called_once_with("unknown-package", "1.0.0")