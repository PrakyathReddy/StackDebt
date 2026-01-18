"""
GitHub Analyzer service for detecting software components from GitHub repositories.

This service analyzes GitHub repositories to detect dependencies and infrastructure
components from package files, Dockerfiles, and configuration files.
It follows Requirements 2.3, 2.4, 2.5, 8.2, and 9.1.
"""

import asyncio
import base64
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from urllib.parse import urlparse

import httpx
import yaml
from app.schemas import Component, ComponentCategory, RiskLevel, ComponentDetectionResult
from app.encyclopedia import EncyclopediaRepository
from app.utils import get_component_weight
from app.external_service_handler import (
    external_service_handler, 
    RetryableError, 
    NonRetryableError, 
    CircuitBreakerOpenError,
    create_fallback_response
)


class GitHubAnalyzer:
    """
    Service for analyzing GitHub repositories to detect software components.
    
    This class implements GitHub API integration to analyze repositories
    and detect components from package files, Dockerfiles, and configuration files.
    """
    
    def __init__(self, encyclopedia: EncyclopediaRepository, github_token: Optional[str] = None):
        """Initialize the analyzer with encyclopedia and optional GitHub token."""
        self.encyclopedia = encyclopedia
        self.github_token = github_token
        self.timeout = httpx.Timeout(30.0)  # 30 second timeout per requirement 8.2
        
        # File patterns for different package managers and configurations
        self.package_files = {
            'package.json': self._parse_package_json,
            'package-lock.json': self._parse_package_lock_json,
            'requirements.txt': self._parse_requirements_txt,
            'pyproject.toml': self._parse_pyproject_toml,
            'setup.py': self._parse_setup_py,
            'go.mod': self._parse_go_mod,
            'go.sum': self._parse_go_sum,
            'pom.xml': self._parse_pom_xml,
            'build.gradle': self._parse_build_gradle,
            'Cargo.toml': self._parse_cargo_toml,
            'composer.json': self._parse_composer_json,
            'Gemfile': self._parse_gemfile,
        }
        
        self.dockerfile_patterns = {
            'Dockerfile': self._parse_dockerfile,
            'docker-compose.yml': self._parse_docker_compose,
            'docker-compose.yaml': self._parse_docker_compose,
        }
        
        self.config_files = {
            '.nvmrc': self._parse_nvmrc,
            '.python-version': self._parse_python_version,
            '.ruby-version': self._parse_ruby_version,
            'runtime.txt': self._parse_runtime_txt,
            'terraform.tf': self._parse_terraform,
            'main.tf': self._parse_terraform,
            'k8s.yaml': self._parse_kubernetes,
            'deployment.yaml': self._parse_kubernetes,
        }

    async def analyze_repository(self, repo_url: str) -> ComponentDetectionResult:
        """
        Analyze a GitHub repository to detect software components.
        
        Args:
            repo_url: The GitHub repository URL to analyze
            
        Returns:
            ComponentDetectionResult with detected components and metadata
            
        Raises:
            httpx.RequestError: For network-related errors
            ValueError: For invalid repository URLs or access issues
        """
        detection_start = datetime.now()
        
        async def _perform_analysis():
            detected_components = []
            failed_detections = []
            
            try:
                # Parse repository URL
                owner, repo = self._parse_github_url(repo_url)
                
                # Get repository contents
                repo_contents = await self._fetch_repository_contents(owner, repo)
                
                # Parse package files
                package_components = await self._parse_package_files(repo_contents, owner, repo)
                detected_components.extend(package_components)
                
                # Parse Dockerfiles
                docker_components = await self._parse_dockerfiles(repo_contents, owner, repo)
                detected_components.extend(docker_components)
                
                # Parse configuration files
                config_components = await self._parse_config_files(repo_contents, owner, repo)
                detected_components.extend(config_components)
                
                # Enrich components with version data from encyclopedia
                enriched_components = []
                for component in detected_components:
                    try:
                        enriched = await self._enrich_component_data(component)
                        enriched_components.append(enriched)
                    except Exception as e:
                        failed_detections.append(f"{component.name}@{component.version}: {str(e)}")
                
                # Remove duplicates based on name and version
                unique_components = self._deduplicate_components(enriched_components)
                
                detection_end = datetime.now()
                detection_time_ms = int((detection_end - detection_start).total_seconds() * 1000)
                
                return ComponentDetectionResult(
                    detected_components=unique_components,
                    failed_detections=failed_detections,
                    detection_metadata={
                        'repository_url': repo_url,
                        'owner': owner,
                        'repo': repo,
                        'files_analyzed': len(repo_contents),
                        'detection_time_ms': detection_time_ms,
                        'analysis_type': 'github'
                    }
                )
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Repository not found or is private: {repo_url}")
                elif e.response.status_code == 403:
                    raise ValueError(f"Access forbidden to repository: {repo_url}. Repository may be private or rate limit exceeded.")
                elif e.response.status_code == 401:
                    raise ValueError(f"Authentication required for repository: {repo_url}. Repository is private.")
                else:
                    raise httpx.RequestError(f"HTTP error {e.response.status_code} when accessing {repo_url}")
            except httpx.TimeoutException:
                raise httpx.RequestError(f"Request to GitHub API timed out after 30 seconds")
            except httpx.ConnectError:
                raise httpx.RequestError(f"Could not connect to GitHub API - service may be unavailable")
        
        try:
            # Execute with retry logic and circuit breaker
            return await external_service_handler.execute_with_retry(
                service_name='github_api',
                operation=_perform_analysis
            )
            
        except CircuitBreakerOpenError as e:
            # Circuit breaker is open, create fallback response
            fallback_data = create_fallback_response('github_api', e, {'repository_url': repo_url})
            return ComponentDetectionResult(
                detected_components=[],
                failed_detections=[f"GitHub API circuit breaker open: {e}"],
                detection_metadata=fallback_data['detection_metadata']
            )
            
        except (RetryableError, NonRetryableError) as e:
            # All retries exhausted or non-retryable error, create fallback response
            fallback_data = create_fallback_response('github_api', e, {'repository_url': repo_url})
            return ComponentDetectionResult(
                detected_components=[],
                failed_detections=[f"GitHub API failure: {e}"],
                detection_metadata=fallback_data['detection_metadata']
            )
            
        except Exception as e:
            # Unexpected error, still try to provide fallback
            fallback_data = create_fallback_response('github_api', e, {'repository_url': repo_url})
            return ComponentDetectionResult(
                detected_components=[],
                failed_detections=[f"Unexpected GitHub API error: {e}"],
                detection_metadata=fallback_data['detection_metadata']
            )

    def _parse_github_url(self, repo_url: str) -> Tuple[str, str]:
        """
        Parse GitHub repository URL to extract owner and repository name.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Tuple of (owner, repo)
            
        Raises:
            ValueError: If URL is not a valid GitHub repository URL
        """
        parsed = urlparse(repo_url)
        
        if parsed.netloc.lower() != 'github.com':
            raise ValueError(f"Not a GitHub repository URL: {repo_url}")
        
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")
        
        owner = path_parts[0]
        repo = path_parts[1]
        
        # Remove .git suffix if present
        if repo.endswith('.git'):
            repo = repo[:-4]
        
        return owner, repo

    async def _fetch_repository_contents(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetch repository contents from GitHub API.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Dictionary mapping file paths to file contents
        """
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'StackDebt-Analyzer/1.0'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Get repository tree
            tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
            tree_response = await client.get(tree_url, headers=headers)
            tree_response.raise_for_status()
            tree_data = tree_response.json()
            
            # Filter for files we're interested in
            relevant_files = []
            all_patterns = {**self.package_files, **self.dockerfile_patterns, **self.config_files}
            
            for item in tree_data.get('tree', []):
                if item['type'] == 'blob':  # Only process files, not directories
                    file_path = item['path']
                    file_name = file_path.split('/')[-1]
                    
                    # Check if this file matches any of our patterns
                    if (file_name in all_patterns or 
                        any(pattern in file_path for pattern in ['Dockerfile', '.tf', '.yaml', '.yml'])):
                        relevant_files.append({
                            'path': file_path,
                            'sha': item['sha'],
                            'url': item['url']
                        })
            
            # Fetch content for relevant files (limit to avoid rate limiting)
            contents = {}
            for file_info in relevant_files[:50]:  # Limit to 50 files to avoid rate limits
                try:
                    content_response = await client.get(file_info['url'], headers=headers)
                    content_response.raise_for_status()
                    content_data = content_response.json()
                    
                    if content_data.get('encoding') == 'base64':
                        file_content = base64.b64decode(content_data['content']).decode('utf-8')
                        contents[file_info['path']] = file_content
                except Exception as e:
                    # Skip files that can't be decoded or fetched
                    continue
            
            return contents

    async def _parse_package_files(self, repo_contents: Dict[str, str], owner: str, repo: str) -> List[Component]:
        """Parse package files to detect dependencies."""
        components = []
        
        for file_path, content in repo_contents.items():
            file_name = file_path.split('/')[-1]
            
            if file_name in self.package_files:
                try:
                    parser = self.package_files[file_name]
                    file_components = await parser(content, file_path)
                    components.extend(file_components)
                except Exception as e:
                    # Log parsing error but continue with other files
                    continue
        
        return components

    async def _parse_dockerfiles(self, repo_contents: Dict[str, str], owner: str, repo: str) -> List[Component]:
        """Parse Dockerfiles to detect base images and installed packages."""
        components = []
        
        for file_path, content in repo_contents.items():
            file_name = file_path.split('/')[-1]
            
            if file_name in self.dockerfile_patterns or 'Dockerfile' in file_name:
                try:
                    if 'docker-compose' in file_name:
                        parser = self._parse_docker_compose
                    else:
                        parser = self._parse_dockerfile
                    
                    file_components = await parser(content, file_path)
                    components.extend(file_components)
                except Exception as e:
                    continue
        
        return components

    async def _parse_config_files(self, repo_contents: Dict[str, str], owner: str, repo: str) -> List[Component]:
        """Parse configuration files to detect infrastructure components."""
        components = []
        
        for file_path, content in repo_contents.items():
            file_name = file_path.split('/')[-1]
            
            # Check exact file name matches
            if file_name in self.config_files:
                try:
                    parser = self.config_files[file_name]
                    file_components = await parser(content, file_path)
                    components.extend(file_components)
                except Exception as e:
                    continue
            
            # Check pattern matches for terraform and kubernetes files
            elif file_name.endswith('.tf'):
                try:
                    file_components = await self._parse_terraform(content, file_path)
                    components.extend(file_components)
                except Exception as e:
                    continue
            elif file_name.endswith(('.yaml', '.yml')) and any(k8s_term in file_path.lower() for k8s_term in ['k8s', 'kubernetes', 'deployment', 'service']):
                try:
                    file_components = await self._parse_kubernetes(content, file_path)
                    components.extend(file_components)
                except Exception as e:
                    continue
        
        return components

    # Package file parsers
    async def _parse_package_json(self, content: str, file_path: str) -> List[Component]:
        """Parse package.json for Node.js dependencies."""
        components = []
        
        try:
            data = json.loads(content)
            
            # Add Node.js engine if specified
            engines = data.get('engines', {})
            if 'node' in engines:
                node_version = engines['node'].strip('^~>=<')
                components.append(Component(
                    name='node.js',
                    version=node_version,
                    release_date=date.today(),
                    category=ComponentCategory.PROGRAMMING_LANGUAGE,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                ))
            
            # Parse dependencies
            all_deps = {}
            all_deps.update(data.get('dependencies', {}))
            all_deps.update(data.get('devDependencies', {}))
            
            for dep_name, version_spec in all_deps.items():
                # Extract version number from version spec
                version = self._extract_version_from_spec(version_spec)
                if version:
                    category = self._categorize_npm_package(dep_name)
                    components.append(Component(
                        name=dep_name,
                        version=version,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
        
        except json.JSONDecodeError:
            pass
        
        return components

    async def _parse_package_lock_json(self, content: str, file_path: str) -> List[Component]:
        """Parse package-lock.json for exact Node.js dependency versions."""
        components = []
        
        try:
            data = json.loads(content)
            packages = data.get('packages', {})
            
            for package_path, package_info in packages.items():
                if package_path == '':  # Root package
                    continue
                
                package_name = package_path.split('node_modules/')[-1]
                version = package_info.get('version')
                
                if version:
                    category = self._categorize_npm_package(package_name)
                    components.append(Component(
                        name=package_name,
                        version=version,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
        
        except json.JSONDecodeError:
            pass
        
        return components

    async def _parse_requirements_txt(self, content: str, file_path: str) -> List[Component]:
        """Parse requirements.txt for Python dependencies."""
        components = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse package==version or package>=version format
                match = re.match(r'^([a-zA-Z0-9_-]+)([><=!]+)([0-9.]+)', line)
                if match:
                    package_name = match.group(1)
                    version = match.group(3)
                    
                    category = self._categorize_python_package(package_name)
                    components.append(Component(
                        name=package_name,
                        version=version,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
        
        return components

    async def _parse_pyproject_toml(self, content: str, file_path: str) -> List[Component]:
        """Parse pyproject.toml for Python project configuration."""
        components = []
        
        try:
            # Simple TOML parsing for dependencies
            lines = content.split('\n')
            in_dependencies = False
            
            for line in lines:
                line = line.strip()
                if line == '[tool.poetry.dependencies]' or line == '[project.dependencies]':
                    in_dependencies = True
                    continue
                elif line.startswith('[') and in_dependencies:
                    in_dependencies = False
                    continue
                
                if in_dependencies and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        package_name = parts[0].strip().strip('"\'')
                        version_spec = parts[1].strip().strip('"\'')
                        version = self._extract_version_from_spec(version_spec)
                        
                        if version and package_name != 'python':
                            category = self._categorize_python_package(package_name)
                            components.append(Component(
                                name=package_name,
                                version=version,
                                release_date=date.today(),
                                category=category,
                                risk_level=RiskLevel.OK,
                                age_years=0.0,
                                weight=get_component_weight(category)
                            ))
                        elif package_name == 'python':
                            # Python version requirement
                            components.append(Component(
                                name='python',
                                version=version,
                                release_date=date.today(),
                                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                                risk_level=RiskLevel.OK,
                                age_years=0.0,
                                weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                            ))
        
        except Exception:
            pass
        
        return components

    async def _parse_setup_py(self, content: str, file_path: str) -> List[Component]:
        """Parse setup.py for Python dependencies."""
        components = []
        
        # Extract install_requires and python_requires
        install_requires_match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if install_requires_match:
            requirements_str = install_requires_match.group(1)
            # Parse individual requirements
            for req in re.findall(r'["\']([^"\']+)["\']', requirements_str):
                match = re.match(r'^([a-zA-Z0-9_-]+)([><=!]+)([0-9.]+)', req)
                if match:
                    package_name = match.group(1)
                    version = match.group(3)
                    
                    category = self._categorize_python_package(package_name)
                    components.append(Component(
                        name=package_name,
                        version=version,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
        
        # Check for Python version requirement
        python_requires_match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)
        if python_requires_match:
            python_version = self._extract_version_from_spec(python_requires_match.group(1))
            if python_version:
                components.append(Component(
                    name='python',
                    version=python_version,
                    release_date=date.today(),
                    category=ComponentCategory.PROGRAMMING_LANGUAGE,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                ))
        
        return components

    async def _parse_go_mod(self, content: str, file_path: str) -> List[Component]:
        """Parse go.mod for Go dependencies."""
        components = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Parse go version
            if line.startswith('go '):
                go_version = line.split()[1]
                components.append(Component(
                    name='go',
                    version=go_version,
                    release_date=date.today(),
                    category=ComponentCategory.PROGRAMMING_LANGUAGE,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                ))
            
            # Parse require dependencies
            elif line.startswith('require ') or (line and not line.startswith(('module ', 'go ', '//', 'replace ', 'exclude '))):
                # Handle both single line and multi-line require blocks
                if line.startswith('require '):
                    dep_line = line[8:].strip()  # Remove 'require '
                else:
                    dep_line = line
                
                if dep_line and not dep_line.startswith('('):
                    parts = dep_line.split()
                    if len(parts) >= 2:
                        module_name = parts[0]
                        version = parts[1].lstrip('v')  # Remove 'v' prefix from version
                        
                        category = self._categorize_go_package(module_name)
                        components.append(Component(
                            name=module_name,
                            version=version,
                            release_date=date.today(),
                            category=category,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(category)
                        ))
        
        return components

    async def _parse_go_sum(self, content: str, file_path: str) -> List[Component]:
        """Parse go.sum for Go dependency checksums (extract versions)."""
        components = []
        seen_modules = set()
        
        for line in content.split('\n'):
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    module_version = parts[0]
                    if ' ' in module_version:
                        module_name, version = module_version.rsplit(' ', 1)
                        version = version.lstrip('v')
                        
                        # Avoid duplicates
                        if (module_name, version) not in seen_modules:
                            seen_modules.add((module_name, version))
                            category = self._categorize_go_package(module_name)
                            components.append(Component(
                                name=module_name,
                                version=version,
                                release_date=date.today(),
                                category=category,
                                risk_level=RiskLevel.OK,
                                age_years=0.0,
                                weight=get_component_weight(category)
                            ))
        
        return components

    async def _parse_pom_xml(self, content: str, file_path: str) -> List[Component]:
        """Parse pom.xml for Java/Maven dependencies."""
        components = []
        
        try:
            root = ET.fromstring(content)
            
            # Handle XML namespaces
            namespaces = {}
            if root.tag.startswith('{'):
                # Extract namespace from root tag
                namespace = root.tag.split('}')[0][1:]
                namespaces['maven'] = namespace
            
            # Find Java version
            java_version = None
            
            if namespaces:
                # Try with namespace
                properties = root.find('.//maven:properties', namespaces)
                if properties is not None:
                    # The element name has dots, so we need to find it differently
                    for child in properties:
                        if child.tag.endswith('maven.compiler.source'):
                            java_version = child.text
                            break
            else:
                # Try without namespace
                properties = root.find('.//properties')
                if properties is not None:
                    java_version_elem = properties.find('maven.compiler.source')
                    if java_version_elem is not None and java_version_elem.text:
                        java_version = java_version_elem.text
            
            if java_version:
                components.append(Component(
                    name='java',
                    version=java_version,
                    release_date=date.today(),
                    category=ComponentCategory.PROGRAMMING_LANGUAGE,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                ))
            
            # Find dependencies
            dependencies = []
            if namespaces:
                dependencies = root.findall('.//maven:dependency', namespaces)
            else:
                dependencies = root.findall('.//dependency')
            
            for dep in dependencies:
                group_id = None
                artifact_id = None
                version = None
                
                if namespaces:
                    group_id = dep.find('maven:groupId', namespaces)
                    artifact_id = dep.find('maven:artifactId', namespaces)
                    version = dep.find('maven:version', namespaces)
                else:
                    group_id = dep.find('groupId')
                    artifact_id = dep.find('artifactId')
                    version = dep.find('version')
                
                if group_id is not None and artifact_id is not None and version is not None:
                    dep_name = f"{group_id.text}:{artifact_id.text}"
                    dep_version = version.text
                    
                    if not dep_version.startswith('${'):  # Skip property references
                        category = self._categorize_java_package(dep_name)
                        components.append(Component(
                            name=dep_name,
                            version=dep_version,
                            release_date=date.today(),
                            category=category,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(category)
                        ))
        
        except ET.ParseError:
            pass
        
        return components

    async def _parse_build_gradle(self, content: str, file_path: str) -> List[Component]:
        """Parse build.gradle for Java/Gradle dependencies."""
        components = []
        
        # Extract Java version
        java_version_match = re.search(r'sourceCompatibility\s*=\s*["\']?([0-9.]+)["\']?', content)
        if java_version_match:
            java_version = java_version_match.group(1)
            components.append(Component(
                name='java',
                version=java_version,
                release_date=date.today(),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
            ))
        
        # Extract dependencies
        # Look for implementation, compile, testImplementation, etc.
        dep_pattern = r'(?:implementation|compile|testImplementation|api|runtimeOnly)\s+["\']([^:]+):([^:]+):([^"\']+)["\']'
        for match in re.finditer(dep_pattern, content):
            group_id = match.group(1)
            artifact_id = match.group(2)
            version = match.group(3)
            
            dep_name = f"{group_id}:{artifact_id}"
            category = self._categorize_java_package(dep_name)
            components.append(Component(
                name=dep_name,
                version=version,
                release_date=date.today(),
                category=category,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(category)
            ))
        
        return components

    async def _parse_cargo_toml(self, content: str, file_path: str) -> List[Component]:
        """Parse Cargo.toml for Rust dependencies."""
        components = []
        
        try:
            lines = content.split('\n')
            in_dependencies = False
            
            for line in lines:
                line = line.strip()
                if line == '[dependencies]':
                    in_dependencies = True
                    continue
                elif line.startswith('[') and in_dependencies:
                    in_dependencies = False
                    continue
                
                if in_dependencies and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        package_name = parts[0].strip()
                        version_spec = parts[1].strip().strip('"\'')
                        version = self._extract_version_from_spec(version_spec)
                        
                        if version:
                            category = ComponentCategory.LIBRARY  # Most Rust crates are libraries
                            components.append(Component(
                                name=package_name,
                                version=version,
                                release_date=date.today(),
                                category=category,
                                risk_level=RiskLevel.OK,
                                age_years=0.0,
                                weight=get_component_weight(category)
                            ))
        
        except Exception:
            pass
        
        return components

    async def _parse_composer_json(self, content: str, file_path: str) -> List[Component]:
        """Parse composer.json for PHP dependencies."""
        components = []
        
        try:
            data = json.loads(content)
            
            # Check for PHP version requirement
            require = data.get('require', {})
            if 'php' in require:
                php_version = self._extract_version_from_spec(require['php'])
                if php_version:
                    components.append(Component(
                        name='php',
                        version=php_version,
                        release_date=date.today(),
                        category=ComponentCategory.PROGRAMMING_LANGUAGE,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                    ))
            
            # Parse dependencies
            all_deps = {}
            all_deps.update(require)
            all_deps.update(data.get('require-dev', {}))
            
            for dep_name, version_spec in all_deps.items():
                if dep_name != 'php':  # Skip PHP itself as we handled it above
                    version = self._extract_version_from_spec(version_spec)
                    if version:
                        category = self._categorize_php_package(dep_name)
                        components.append(Component(
                            name=dep_name,
                            version=version,
                            release_date=date.today(),
                            category=category,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(category)
                        ))
        
        except json.JSONDecodeError:
            pass
        
        return components

    async def _parse_gemfile(self, content: str, file_path: str) -> List[Component]:
        """Parse Gemfile for Ruby dependencies."""
        components = []
        
        # Extract Ruby version
        ruby_version_match = re.search(r'ruby\s+["\']([^"\']+)["\']', content)
        if ruby_version_match:
            ruby_version = ruby_version_match.group(1)
            components.append(Component(
                name='ruby',
                version=ruby_version,
                release_date=date.today(),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
            ))
        
        # Extract gem dependencies
        gem_pattern = r'gem\s+["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])?'
        for match in re.finditer(gem_pattern, content):
            gem_name = match.group(1)
            version_spec = match.group(2) if match.group(2) else None
            
            if version_spec:
                version = self._extract_version_from_spec(version_spec)
                if version:
                    category = ComponentCategory.LIBRARY  # Most gems are libraries
                    components.append(Component(
                        name=gem_name,
                        version=version,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
        
        return components

    # Dockerfile parsers
    async def _parse_dockerfile(self, content: str, file_path: str) -> List[Component]:
        """Parse Dockerfile for base images and installed packages."""
        components = []
        
        # Handle multi-line commands by joining lines that end with backslash
        lines = content.split('\n')
        processed_lines = []
        current_line = ""
        
        for line in lines:
            line = line.strip()
            if line.endswith('\\'):
                current_line += line[:-1] + " "
            else:
                current_line += line
                if current_line.strip():
                    processed_lines.append(current_line.strip())
                current_line = ""
        
        # Add any remaining line
        if current_line.strip():
            processed_lines.append(current_line.strip())
        
        for line in processed_lines:
            # Parse FROM statements for base images
            if line.upper().startswith('FROM '):
                image_spec = line[5:].strip()
                # Remove 'as alias' part if present
                if ' as ' in image_spec.lower():
                    image_spec = image_spec.split(' as ')[0].strip()
                
                # Parse image:tag format
                if ':' in image_spec:
                    image_name, tag = image_spec.rsplit(':', 1)
                    
                    # Categorize base image
                    category = self._categorize_docker_image(image_name)
                    components.append(Component(
                        name=image_name,
                        version=tag,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
            
            # Parse RUN commands for package installations
            elif line.upper().startswith('RUN '):
                run_command = line[4:].strip()
                
                # Detect package manager commands
                if 'apt-get install' in run_command or 'apt install' in run_command:
                    packages = self._extract_apt_packages(run_command)
                    for package in packages:
                        components.append(Component(
                            name=package,
                            version='unknown',
                            release_date=date.today(),
                            category=ComponentCategory.LIBRARY,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(ComponentCategory.LIBRARY)
                        ))
                
                elif 'yum install' in run_command or 'dnf install' in run_command:
                    packages = self._extract_yum_packages(run_command)
                    for package in packages:
                        components.append(Component(
                            name=package,
                            version='unknown',
                            release_date=date.today(),
                            category=ComponentCategory.LIBRARY,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(ComponentCategory.LIBRARY)
                        ))
        
        return components

    async def _parse_docker_compose(self, content: str, file_path: str) -> List[Component]:
        """Parse docker-compose.yml for service images and configurations."""
        components = []
        
        try:
            data = yaml.safe_load(content)
            
            # Parse services
            services = data.get('services', {})
            for service_name, service_config in services.items():
                # Parse image specifications
                image = service_config.get('image')
                if image:
                    if ':' in image:
                        image_name, tag = image.rsplit(':', 1)
                    else:
                        image_name, tag = image, 'latest'
                    
                    category = self._categorize_docker_image(image_name)
                    components.append(Component(
                        name=image_name,
                        version=tag,
                        release_date=date.today(),
                        category=category,
                        risk_level=RiskLevel.OK,
                        age_years=0.0,
                        weight=get_component_weight(category)
                    ))
        
        except yaml.YAMLError:
            pass
        
        return components

    # Configuration file parsers
    async def _parse_nvmrc(self, content: str, file_path: str) -> List[Component]:
        """Parse .nvmrc for Node.js version."""
        version = content.strip().lstrip('v')
        if version:
            return [Component(
                name='node.js',
                version=version,
                release_date=date.today(),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
            )]
        return []

    async def _parse_python_version(self, content: str, file_path: str) -> List[Component]:
        """Parse .python-version for Python version."""
        version = content.strip()
        if version:
            return [Component(
                name='python',
                version=version,
                release_date=date.today(),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
            )]
        return []

    async def _parse_ruby_version(self, content: str, file_path: str) -> List[Component]:
        """Parse .ruby-version for Ruby version."""
        version = content.strip()
        if version:
            return [Component(
                name='ruby',
                version=version,
                release_date=date.today(),
                category=ComponentCategory.PROGRAMMING_LANGUAGE,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
            )]
        return []

    async def _parse_runtime_txt(self, content: str, file_path: str) -> List[Component]:
        """Parse runtime.txt (Heroku) for runtime version."""
        components = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line:
                # Parse python-3.9.0 or node-14.17.0 format
                if '-' in line:
                    runtime, version = line.split('-', 1)
                    if runtime in ['python', 'node', 'ruby']:
                        components.append(Component(
                            name=runtime if runtime != 'node' else 'node.js',
                            version=version,
                            release_date=date.today(),
                            category=ComponentCategory.PROGRAMMING_LANGUAGE,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(ComponentCategory.PROGRAMMING_LANGUAGE)
                        ))
        
        return components

    async def _parse_terraform(self, content: str, file_path: str) -> List[Component]:
        """Parse Terraform files for infrastructure components."""
        components = []
        
        # Look for provider blocks
        provider_pattern = r'provider\s+"([^"]+)"\s*{'
        for match in re.finditer(provider_pattern, content):
            provider_name = match.group(1)
            components.append(Component(
                name=f"terraform-{provider_name}",
                version='unknown',
                release_date=date.today(),
                category=ComponentCategory.DEVELOPMENT_TOOL,
                risk_level=RiskLevel.OK,
                age_years=0.0,
                weight=get_component_weight(ComponentCategory.DEVELOPMENT_TOOL)
            ))
        
        # Look for resource blocks to identify services
        resource_pattern = r'resource\s+"([^"]+)"\s+"[^"]+"\s*{'
        for match in re.finditer(resource_pattern, content):
            resource_type = match.group(1)
            # Extract service name from resource type (e.g., aws_instance -> aws)
            if '_' in resource_type:
                service_name = resource_type.split('_')[0]
                components.append(Component(
                    name=service_name,
                    version='unknown',
                    release_date=date.today(),
                    category=ComponentCategory.DEVELOPMENT_TOOL,
                    risk_level=RiskLevel.OK,
                    age_years=0.0,
                    weight=get_component_weight(ComponentCategory.DEVELOPMENT_TOOL)
                ))
        
        return components

    async def _parse_kubernetes(self, content: str, file_path: str) -> List[Component]:
        """Parse Kubernetes YAML files for container images."""
        components = []
        
        try:
            # Handle multiple YAML documents
            for doc in yaml.safe_load_all(content):
                if not doc:
                    continue
                
                # Look for container images in various places
                containers = []
                
                # Deployment, Pod, etc.
                if doc.get('spec', {}).get('template', {}).get('spec', {}).get('containers'):
                    containers = doc['spec']['template']['spec']['containers']
                elif doc.get('spec', {}).get('containers'):
                    containers = doc['spec']['containers']
                
                for container in containers:
                    image = container.get('image')
                    if image:
                        if ':' in image:
                            image_name, tag = image.rsplit(':', 1)
                        else:
                            image_name, tag = image, 'latest'
                        
                        category = self._categorize_docker_image(image_name)
                        components.append(Component(
                            name=image_name,
                            version=tag,
                            release_date=date.today(),
                            category=category,
                            risk_level=RiskLevel.OK,
                            age_years=0.0,
                            weight=get_component_weight(category)
                        ))
        
        except yaml.YAMLError:
            pass
        
        return components

    # Helper methods for categorization and version extraction
    def _categorize_npm_package(self, package_name: str) -> ComponentCategory:
        """Categorize npm packages by name patterns."""
        frameworks = ['react', 'vue', 'angular', 'express', 'next', 'nuxt', 'svelte']
        databases = ['mongodb', 'mysql', 'postgres', 'redis', 'sqlite']
        
        if any(fw in package_name.lower() for fw in frameworks):
            return ComponentCategory.FRAMEWORK
        elif any(db in package_name.lower() for db in databases):
            return ComponentCategory.DATABASE
        else:
            return ComponentCategory.LIBRARY

    def _categorize_python_package(self, package_name: str) -> ComponentCategory:
        """Categorize Python packages by name patterns."""
        frameworks = ['django', 'flask', 'fastapi', 'tornado', 'pyramid']
        databases = ['psycopg2', 'pymongo', 'redis', 'sqlalchemy']
        
        if any(fw in package_name.lower() for fw in frameworks):
            return ComponentCategory.FRAMEWORK
        elif any(db in package_name.lower() for db in databases):
            return ComponentCategory.DATABASE
        else:
            return ComponentCategory.LIBRARY

    def _categorize_go_package(self, package_name: str) -> ComponentCategory:
        """Categorize Go packages by name patterns."""
        frameworks = ['gin', 'echo', 'fiber', 'beego']
        databases = ['mongo', 'redis', 'postgres', 'mysql']
        
        if any(fw in package_name.lower() for fw in frameworks):
            return ComponentCategory.FRAMEWORK
        elif any(db in package_name.lower() for db in databases):
            return ComponentCategory.DATABASE
        else:
            return ComponentCategory.LIBRARY

    def _categorize_java_package(self, package_name: str) -> ComponentCategory:
        """Categorize Java packages by name patterns."""
        frameworks = ['spring', 'hibernate', 'struts', 'jersey']
        databases = ['mysql', 'postgres', 'mongodb', 'redis']
        
        if any(fw in package_name.lower() for fw in frameworks):
            return ComponentCategory.FRAMEWORK
        elif any(db in package_name.lower() for db in databases):
            return ComponentCategory.DATABASE
        else:
            return ComponentCategory.LIBRARY

    def _categorize_php_package(self, package_name: str) -> ComponentCategory:
        """Categorize PHP packages by name patterns."""
        frameworks = ['laravel', 'symfony', 'codeigniter', 'zend']
        databases = ['doctrine', 'eloquent', 'mongodb', 'redis']
        
        if any(fw in package_name.lower() for fw in frameworks):
            return ComponentCategory.FRAMEWORK
        elif any(db in package_name.lower() for db in databases):
            return ComponentCategory.DATABASE
        else:
            return ComponentCategory.LIBRARY

    def _categorize_docker_image(self, image_name: str) -> ComponentCategory:
        """Categorize Docker images by name patterns."""
        # Remove registry prefix if present
        if '/' in image_name:
            image_name = image_name.split('/')[-1]
        
        operating_systems = ['ubuntu', 'debian', 'centos', 'alpine', 'fedora', 'rhel']
        languages = ['python', 'node', 'java', 'golang', 'ruby', 'php']
        databases = ['postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch']
        web_servers = ['nginx', 'apache', 'httpd']
        
        if any(os_name in image_name.lower() for os_name in operating_systems):
            return ComponentCategory.OPERATING_SYSTEM
        elif any(lang in image_name.lower() for lang in languages):
            return ComponentCategory.PROGRAMMING_LANGUAGE
        elif any(db in image_name.lower() for db in databases):
            return ComponentCategory.DATABASE
        elif any(ws in image_name.lower() for ws in web_servers):
            return ComponentCategory.WEB_SERVER
        else:
            return ComponentCategory.LIBRARY

    def _extract_version_from_spec(self, version_spec: str) -> Optional[str]:
        """Extract version number from version specification."""
        if not version_spec:
            return None
        
        # Remove common prefixes and operators
        version_spec = version_spec.strip('^~>=<!')
        
        # Extract version number pattern
        version_match = re.search(r'(\d+(?:\.\d+)*(?:\.\d+)?)', version_spec)
        if version_match:
            return version_match.group(1)
        
        return None

    def _extract_apt_packages(self, command: str) -> List[str]:
        """Extract package names from apt install command."""
        packages = []
        
        # Handle line continuations by removing backslashes and joining lines
        command = command.replace('\\\n', ' ').replace('\\', ' ')
        
        # Remove common flags and split by spaces
        command = re.sub(r'-[a-zA-Z]+', '', command)  # Remove flags like -y
        parts = command.split()
        
        # Find packages after 'install'
        install_index = -1
        for i, part in enumerate(parts):
            if part == 'install':
                install_index = i
                break
        
        if install_index >= 0:
            for part in parts[install_index + 1:]:
                if part and not part.startswith('-') and '=' not in part and part != '&&' and not part.startswith('rm'):
                    # Filter out common non-package words
                    if part not in ['update', 'upgrade', 'clean', 'autoremove', 'autoclean', '/var/lib/apt/lists/*']:
                        packages.append(part)
        
        return packages

    def _extract_yum_packages(self, command: str) -> List[str]:
        """Extract package names from yum/dnf install command."""
        packages = []
        
        # Remove common flags and split by spaces
        command = re.sub(r'-[a-zA-Z]+', '', command)  # Remove flags like -y
        parts = command.split()
        
        # Find packages after 'install'
        install_index = -1
        for i, part in enumerate(parts):
            if part == 'install':
                install_index = i
                break
        
        if install_index >= 0:
            for part in parts[install_index + 1:]:
                if part and not part.startswith('-'):
                    packages.append(part)
        
        return packages

    def _deduplicate_components(self, components: List[Component]) -> List[Component]:
        """Remove duplicate components based on name and version."""
        seen = set()
        unique_components = []
        
        for component in components:
            key = (component.name, component.version)
            if key not in seen:
                seen.add(key)
                unique_components.append(component)
        
        return unique_components

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
                from app.utils import calculate_age_years, determine_risk_level
                
                age_years = calculate_age_years(version_info.release_date)
                risk_level = determine_risk_level(age_years, version_info.end_of_life_date)
                
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