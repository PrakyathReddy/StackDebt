"""
Property-based test for GitHub analysis completeness.

**Feature: stackdebt, Property 4: GitHub Analysis Completeness**
**Validates: Requirements 2.3, 2.4, 2.5**

Property: For any GitHub repository analysis, the system should detect components 
from all supported file types (package files, Dockerfiles, config files) present 
in the repository.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import AsyncMock, patch
from datetime import date
import json
import yaml

from app.github_analyzer import GitHubAnalyzer
from app.encyclopedia import EncyclopediaRepository
from app.schemas import Component, ComponentCategory, RiskLevel, ComponentDetectionResult


# Strategy for generating valid package.json content
@st.composite
def package_json_content(draw):
    """Generate valid package.json content with dependencies."""
    dependencies = draw(st.dictionaries(
        st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'),
        st.text(min_size=1, max_size=10, alphabet='0123456789.'),
        min_size=0, max_size=5
    ))
    
    engines = {}
    if draw(st.booleans()):
        engines['node'] = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.'))
    
    package_data = {
        "name": draw(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz')),
        "version": draw(st.text(min_size=1, max_size=10, alphabet='0123456789.')),
        "dependencies": dependencies
    }
    
    if engines:
        package_data["engines"] = engines
    
    return json.dumps(package_data)


# Strategy for generating valid requirements.txt content
@st.composite
def requirements_txt_content(draw):
    """Generate valid requirements.txt content."""
    num_requirements = draw(st.integers(min_value=0, max_value=10))
    requirements = []
    
    for _ in range(num_requirements):
        package_name = draw(st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_'))
        version = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.'))
        operator = draw(st.sampled_from(['==', '>=', '<=', '>', '<', '~=']))
        requirements.append(f"{package_name}{operator}{version}")
    
    return '\n'.join(requirements)


# Strategy for generating valid go.mod content
@st.composite
def go_mod_content(draw):
    """Generate valid go.mod content."""
    module_name = draw(st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789./-'))
    go_version = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.'))
    
    num_deps = draw(st.integers(min_value=0, max_value=5))
    dependencies = []
    
    for _ in range(num_deps):
        dep_name = draw(st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789./-'))
        dep_version = draw(st.text(min_size=1, max_size=15, alphabet='0123456789.-'))
        dependencies.append(f"    {dep_name} v{dep_version}")
    
    content = f"module {module_name}\n\ngo {go_version}\n"
    if dependencies:
        content += "\nrequire (\n" + '\n'.join(dependencies) + "\n)\n"
    
    return content


# Strategy for generating valid Dockerfile content
@st.composite
def dockerfile_content(draw):
    """Generate valid Dockerfile content."""
    base_images = ['python', 'node', 'ubuntu', 'alpine', 'nginx', 'postgres']
    base_image = draw(st.sampled_from(base_images))
    tag = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.-'))
    
    content = f"FROM {base_image}:{tag}\n"
    
    # Add some RUN commands with package installations
    if draw(st.booleans()):
        packages = draw(st.lists(
            st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-'),
            min_size=1, max_size=5
        ))
        content += f"RUN apt-get update && apt-get install -y {' '.join(packages)}\n"
    
    return content


# Strategy for generating valid docker-compose.yml content
@st.composite
def docker_compose_content(draw):
    """Generate valid docker-compose.yml content."""
    services = {}
    num_services = draw(st.integers(min_value=1, max_value=3))
    
    for i in range(num_services):
        service_name = f"service{i}"
        base_images = ['nginx', 'postgres', 'redis', 'mysql', 'mongodb']
        image = draw(st.sampled_from(base_images))
        tag = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.-'))
        
        services[service_name] = {
            'image': f"{image}:{tag}"
        }
    
    compose_data = {
        'version': '3.8',
        'services': services
    }
    
    return yaml.dump(compose_data)


# Strategy for generating repository contents
@st.composite
def repository_contents(draw):
    """Generate repository contents with various file types."""
    contents = {}
    
    # Package files
    if draw(st.booleans()):
        contents['package.json'] = draw(package_json_content())
    
    if draw(st.booleans()):
        contents['requirements.txt'] = draw(requirements_txt_content())
    
    if draw(st.booleans()):
        contents['go.mod'] = draw(go_mod_content())
    
    # Dockerfile
    if draw(st.booleans()):
        contents['Dockerfile'] = draw(dockerfile_content())
    
    # Docker compose
    if draw(st.booleans()):
        contents['docker-compose.yml'] = draw(docker_compose_content())
    
    # Config files
    if draw(st.booleans()):
        contents['.nvmrc'] = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.v'))
    
    if draw(st.booleans()):
        contents['.python-version'] = draw(st.text(min_size=1, max_size=10, alphabet='0123456789.'))
    
    return contents


class TestGitHubAnalysisCompletenessProperty:
    """Property-based tests for GitHub analysis completeness."""

    def create_analyzer(self):
        """Create a GitHub analyzer instance with mock encyclopedia."""
        mock = AsyncMock(spec=EncyclopediaRepository)
        mock.lookup_version.return_value = None  # No version data found
        return GitHubAnalyzer(mock)

    @given(repo_contents=repository_contents())
    @settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_github_analysis_completeness(self, repo_contents):
        """
        **Feature: stackdebt, Property 4: GitHub Analysis Completeness**
        **Validates: Requirements 2.3, 2.4, 2.5**
        
        Property: For any GitHub repository analysis, the system should detect components 
        from all supported file types (package files, Dockerfiles, config files) present 
        in the repository.
        """
        analyzer = self.create_analyzer()
        assume(len(repo_contents) > 0)  # Need at least one file to analyze
        
        # Mock the GitHub API calls
        with patch.object(analyzer, '_fetch_repository_contents', return_value=repo_contents):
            with patch.object(analyzer, '_parse_github_url', return_value=('owner', 'repo')):
                result = await analyzer.analyze_repository('https://github.com/owner/repo')
        
        # Verify result structure
        assert isinstance(result, ComponentDetectionResult)
        assert isinstance(result.detected_components, list)
        assert isinstance(result.failed_detections, list)
        assert isinstance(result.detection_metadata, dict)
        
        # Property: Should detect components from all supported file types present
        expected_detections = set()
        
        # Check package files
        if 'package.json' in repo_contents:
            expected_detections.add('package_json')
            # Should detect Node.js dependencies
            try:
                package_data = json.loads(repo_contents['package.json'])
                if 'engines' in package_data and 'node' in package_data['engines']:
                    assert any(c.name == 'node.js' for c in result.detected_components), \
                        "Should detect Node.js from package.json engines"
                if 'dependencies' in package_data:
                    dep_names = set(package_data['dependencies'].keys())
                    detected_names = {c.name for c in result.detected_components}
                    # At least some dependencies should be detected
                    if dep_names:
                        assert len(dep_names.intersection(detected_names)) > 0, \
                            "Should detect at least some dependencies from package.json"
            except (json.JSONDecodeError, KeyError):
                pass  # Invalid JSON is handled gracefully
        
        if 'requirements.txt' in repo_contents:
            expected_detections.add('requirements_txt')
            # Should detect Python packages
            lines = [line.strip() for line in repo_contents['requirements.txt'].split('\n') if line.strip()]
            if lines:
                # At least some packages should be detected
                detected_names = {c.name for c in result.detected_components}
                package_names = set()
                for line in lines:
                    if '==' in line or '>=' in line or '<=' in line:
                        package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0]
                        package_names.add(package_name)
                
                if package_names:
                    assert len(package_names.intersection(detected_names)) > 0, \
                        "Should detect at least some packages from requirements.txt"
        
        if 'go.mod' in repo_contents:
            expected_detections.add('go_mod')
            # Should detect Go version and dependencies
            if 'go ' in repo_contents['go.mod']:
                assert any(c.name == 'go' for c in result.detected_components), \
                    "Should detect Go version from go.mod"
        
        # Check Dockerfiles
        if 'Dockerfile' in repo_contents:
            expected_detections.add('dockerfile')
            # Should detect base images
            dockerfile_content = repo_contents['Dockerfile']
            if 'FROM ' in dockerfile_content:
                # Should detect at least one base image
                base_images = []
                for line in dockerfile_content.split('\n'):
                    if line.strip().upper().startswith('FROM '):
                        image_spec = line.strip()[5:].strip()
                        if ':' in image_spec:
                            image_name = image_spec.split(':')[0]
                            base_images.append(image_name)
                
                if base_images:
                    detected_names = {c.name for c in result.detected_components}
                    assert len(set(base_images).intersection(detected_names)) > 0, \
                        "Should detect at least one base image from Dockerfile"
        
        if 'docker-compose.yml' in repo_contents:
            expected_detections.add('docker_compose')
            # Should detect service images
            try:
                compose_data = yaml.safe_load(repo_contents['docker-compose.yml'])
                if 'services' in compose_data:
                    service_images = []
                    for service_config in compose_data['services'].values():
                        if 'image' in service_config:
                            image = service_config['image']
                            if ':' in image:
                                image_name = image.split(':')[0]
                                service_images.append(image_name)
                    
                    if service_images:
                        detected_names = {c.name for c in result.detected_components}
                        assert len(set(service_images).intersection(detected_names)) > 0, \
                            "Should detect at least one service image from docker-compose.yml"
            except yaml.YAMLError:
                pass  # Invalid YAML is handled gracefully
        
        # Check config files
        if '.nvmrc' in repo_contents:
            expected_detections.add('nvmrc')
            # Should detect Node.js version
            assert any(c.name == 'node.js' for c in result.detected_components), \
                "Should detect Node.js version from .nvmrc"
        
        if '.python-version' in repo_contents:
            expected_detections.add('python_version')
            # Should detect Python version
            assert any(c.name == 'python' for c in result.detected_components), \
                "Should detect Python version from .python-version"
        
        # Property: Analysis metadata should reflect the files analyzed
        assert result.detection_metadata['files_analyzed'] == len(repo_contents), \
            "Metadata should reflect the number of files analyzed"
        
        assert result.detection_metadata['analysis_type'] == 'github', \
            "Analysis type should be 'github'"
        
        # Property: Detection time should be reasonable (< 30 seconds per requirement 8.2)
        assert result.detection_metadata['detection_time_ms'] < 30000, \
            "Detection should complete within 30 seconds"
        
        # Property: All detected components should have valid structure
        for component in result.detected_components:
            assert isinstance(component, Component), \
                "All detected items should be Component instances"
            
            assert component.name, \
                "All components should have non-empty names"
            
            assert component.version, \
                "All components should have versions (even if 'unknown')"
            
            assert isinstance(component.category, (ComponentCategory, str)), \
                "All components should have valid categories"
            
            assert isinstance(component.risk_level, (RiskLevel, str)), \
                "All components should have valid risk levels"
            
            assert component.age_years >= 0, \
                "Component age should be non-negative"
            
            assert 0 <= component.weight <= 1, \
                "Component weight should be between 0 and 1"
        
        # Property: No duplicate components (same name and version)
        seen_components = set()
        for component in result.detected_components:
            component_key = (component.name, component.version)
            assert component_key not in seen_components, \
                f"Duplicate component detected: {component.name} {component.version}"
            seen_components.add(component_key)

    @given(st.text(min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_invalid_file_content_handling(self, invalid_content):
        """
        Property: Invalid file content should be handled gracefully without crashing.
        """
        analyzer = self.create_analyzer()
        # Test with various invalid content types
        test_files = {
            'package.json': invalid_content,
            'requirements.txt': invalid_content,
            'go.mod': invalid_content,
            'Dockerfile': invalid_content,
            'docker-compose.yml': invalid_content
        }
        
        with patch.object(analyzer, '_fetch_repository_contents', return_value=test_files):
            with patch.object(analyzer, '_parse_github_url', return_value=('owner', 'repo')):
                # Should not raise an exception
                result = await analyzer.analyze_repository('https://github.com/owner/repo')
        
        # Should return a valid result even with invalid content
        assert isinstance(result, ComponentDetectionResult)
        assert isinstance(result.detected_components, list)
        assert isinstance(result.failed_detections, list)

    @given(st.integers(min_value=0, max_value=100))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @pytest.mark.asyncio
    async def test_property_empty_repository_handling(self, num_empty_files):
        """
        Property: Empty repositories or repositories with only empty files should be handled gracefully.
        """
        analyzer = self.create_analyzer()
        # Create repository with empty files
        empty_contents = {}
        for i in range(num_empty_files):
            filename = f"empty_file_{i}.txt"
            empty_contents[filename] = ""
        
        with patch.object(analyzer, '_fetch_repository_contents', return_value=empty_contents):
            with patch.object(analyzer, '_parse_github_url', return_value=('owner', 'repo')):
                result = await analyzer.analyze_repository('https://github.com/owner/repo')
        
        # Should return valid result with no components
        assert isinstance(result, ComponentDetectionResult)
        assert isinstance(result.detected_components, list)
        assert len(result.detected_components) == 0  # No components from empty files
        assert result.detection_metadata['files_analyzed'] == num_empty_files