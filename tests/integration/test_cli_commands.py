"""Integration tests for CLI commands.

Tests the CLI interface following TDD approach for Task 1.3.3.
"""

import json
import tempfile
from pathlib import Path
from click.testing import CliRunner
import pytest


def test_cli_load_command(sample_s2p_file):
    """Test CLI load command loads SNP file and displays summary."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['load', str(sample_s2p_file)])
    
    assert result.exit_code == 0
    assert 'Loaded' in result.output
    assert 'port' in result.output.lower()
    assert 'frequency' in result.output.lower()


def test_cli_load_json_output(sample_s2p_file):
    """Test CLI load command with JSON output format."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['load', str(sample_s2p_file), '--json'])
    
    assert result.exit_code == 0
    
    # Parse JSON output
    data = json.loads(result.output)
    assert data['status'] == 'success'
    assert 'network' in data
    assert 'port_count' in data['network']
    assert 'frequency_range_ghz' in data['network']


def test_cli_load_validate_only(sample_s2p_file):
    """Test CLI load with validate-only flag."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['load', str(sample_s2p_file), '--validate-only'])
    
    assert result.exit_code == 0
    assert 'valid' in result.output.lower() or 'success' in result.output.lower()


def test_cli_load_invalid_file():
    """Test CLI load command with invalid file."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['load', 'nonexistent.s2p'])
    
    assert result.exit_code != 0


def test_cli_info_command(sample_s2p_file):
    """Test CLI info command displays network information."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    # First load a file
    runner.invoke(cli, ['load', str(sample_s2p_file)])
    
    # Then get info
    result = runner.invoke(cli, ['info'])
    
    assert result.exit_code == 0
    assert 'network' in result.output.lower() or 'port' in result.output.lower()


def test_cli_add_component(sample_s2p_file):
    """Test CLI add-component command."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    # First load a file
    runner.invoke(cli, ['load', str(sample_s2p_file)])
    
    # Then add a component
    result = runner.invoke(cli, [
        'add-component',
        '--port', '1',
        '--type', 'cap',
        '--value', '10pF',
        '--placement', 'series'
    ])
    
    assert result.exit_code == 0
    assert 'added' in result.output.lower() or 'success' in result.output.lower()


def test_cli_add_component_without_network():
    """Test CLI add-component fails without loaded network."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, [
        'add-component',
        '--port', '1',
        '--type', 'cap',
        '--value', '10pF',
        '--placement', 'series'
    ])
    
    assert result.exit_code != 0


def test_cli_add_component_json_output(sample_s2p_file):
    """Test CLI add-component with JSON output."""
    from snp_tool.cli.commands import cli
    
    runner = CliRunner()
    # First load a file
    runner.invoke(cli, ['load', str(sample_s2p_file)])
    
    # Add component with JSON output
    result = runner.invoke(cli, [
        'add-component',
        '--port', '1',
        '--type', 'cap',
        '--value', '10pF',
        '--placement', 'series',
        '--json'
    ])
    
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert 'status' in data


# Fixtures
@pytest.fixture
def sample_s2p_file(tmp_path):
    """Create a sample S2P file for testing."""
    # Use RI format to avoid confusion with MA format
    s2p_content = """# MHz S RI R 50
! Sample 2-port network
1000 0.5 0.3 0.8 -0.1 0.8 -0.1 0.5 0.3
2000 0.4 0.2 0.7 -0.2 0.7 -0.2 0.4 0.2
3000 0.3 0.1 0.6 -0.3 0.6 -0.3 0.3 0.1
"""
    
    s2p_file = tmp_path / "test.s2p"
    s2p_file.write_text(s2p_content)
    return s2p_file
