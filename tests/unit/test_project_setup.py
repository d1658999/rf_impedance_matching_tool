"""
Unit tests for project setup verification.

Tests verify that:
- All required dependencies are installed correctly
- pyproject.toml has correct dependency specifications
- Package version is accessible
- Basic imports work
"""

import sys
from pathlib import Path

import pytest


def test_dependencies_installed():
    """Test that all required dependencies can be imported."""
    # Core dependencies
    import numpy
    import skrf  # scikit-rf
    import matplotlib
    
    # New dependencies from research.md
    import scipy
    from pythonjsonlogger import jsonlogger
    
    # All imports successful
    assert True


def test_scipy_version():
    """Test that scipy version is >=1.9.0 per research.md Decision 2."""
    import scipy
    
    version_parts = scipy.__version__.split('.')
    major = int(version_parts[0])
    minor = int(version_parts[1])
    
    # scipy>=1.9.0 required for differential_evolution
    assert major > 1 or (major == 1 and minor >= 9), \
        f"scipy version {scipy.__version__} < 1.9.0 required"


def test_package_version():
    """Test that snp_tool package has accessible version."""
    import snp_tool
    
    assert hasattr(snp_tool, '__version__')
    assert isinstance(snp_tool.__version__, str)
    assert len(snp_tool.__version__) > 0
    
    # Verify version follows semantic versioning pattern
    version_parts = snp_tool.__version__.split('.')
    assert len(version_parts) >= 2, "Version should be at least MAJOR.MINOR format"


def test_pyproject_dependencies():
    """Test that pyproject.toml has correct dependencies listed."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # Python 3.9-3.10
    
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    
    with open(pyproject_path, 'rb') as f:
        pyproject = tomllib.load(f)
    
    dependencies = pyproject['project']['dependencies']
    
    # Check core dependencies
    required_deps = {
        'numpy>=1.21.0',
        'scikit-rf>=0.29.0', 
        'matplotlib>=3.5.0',
        'scipy>=1.9.0',
        'python-json-logger>=2.0.0',
    }
    
    # Convert dependencies to set for comparison
    dep_set = set(dependencies)
    
    # Check all required dependencies are present
    for required in required_deps:
        # Check if dependency name matches (with or without version constraint)
        dep_name = required.split('>=')[0].split('==')[0]
        assert any(dep_name in d for d in dep_set), \
            f"Missing required dependency: {required}"


def test_optional_dependencies():
    """Test that optional dependencies are properly specified."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # Python 3.9-3.10
    
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    
    with open(pyproject_path, 'rb') as f:
        pyproject = tomllib.load(f)
    
    optional = pyproject['project']['optional-dependencies']
    
    # Check GUI dependencies
    assert 'gui' in optional
    assert any('PyQt6' in dep for dep in optional['gui'])
    
    # Check dev dependencies  
    assert 'dev' in optional
    dev_deps = optional['dev']
    assert any('pytest' in dep for dep in dev_deps)
    assert any('black' in dep for dep in dev_deps)
    assert any('mypy' in dep for dep in dev_deps)


def test_pytest_runs():
    """Test that pytest is installed and can discover tests."""
    # If this test runs, pytest is working
    assert True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
