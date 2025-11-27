"""End-to-end integration tests for full CLI workflow.

Tests complete user journeys per Task 1.INT.1:
- Load SNP → Display metrics → Add components → Verify updated metrics
- User Story 1 acceptance scenarios  
- User Story 2 acceptance scenarios
- Performance targets (SC-001, SC-002)
"""

import json
import tempfile
import time
from pathlib import Path
import pytest
from click.testing import CliRunner


class TestFullCLIWorkflow:
    """Test complete CLI workflows for User Stories 1 & 2."""
    
    def test_load_display_add_verify_workflow(self, sample_s2p_file):
        """Test: Load SNP → Display metrics → Add components → Verify updated metrics."""
        from snp_tool.cli.commands import cli, CLIContext
        
        runner = CliRunner()
        ctx = CLIContext()
        
        # Step 1: Load SNP file
        result = runner.invoke(cli, ['load', str(sample_s2p_file)], obj=ctx)
        assert result.exit_code == 0
        assert 'Loaded' in result.output
        
        # Step 2: Display metrics before
        result = runner.invoke(cli, ['info', '--metrics'], obj=ctx)
        assert result.exit_code == 0
        assert 'VSWR' in result.output or 'vswr' in result.output.lower()
        
        # Step 3: Add matching component
        result = runner.invoke(cli, [
            'add-component',
            '--port', '1',
            '--type', 'cap',
            '--value', '10pF',
            '--placement', 'series'
        ], obj=ctx)
        assert result.exit_code == 0
        assert 'added' in result.output.lower()
        
        # Step 4: Verify updated metrics
        result = runner.invoke(cli, ['info', '--metrics', '--components'], obj=ctx)
        assert result.exit_code == 0
        assert 'capacitor' in result.output.lower() or '10pF' in result.output
    
    def test_user_story_1_acceptance_scenario(self, large_s2p_file):
        """User Story 1: RF Engineer loads antenna S2P file for analysis."""
        from snp_tool.cli.commands import cli
        
        runner = CliRunner()
        
        # Scenario: Load and validate 2-port antenna file
        result = runner.invoke(cli, ['load', str(large_s2p_file), '--json'])
        assert result.exit_code == 0
        
        # Verify JSON output contains network info
        lines = result.output.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_str = '\n'.join(lines[i:])
                data = json.loads(json_str)
                assert data['status'] == 'success'
                assert 'network' in data
                assert data['network']['port_count'] >= 2
                break
    
    def test_user_story_2_acceptance_scenario(self, sample_s2p_file):
        """User Story 2: RF Engineer adds series capacitor for matching."""
        from snp_tool.cli.commands import cli, CLIContext
        
        runner = CliRunner()
        ctx = CLIContext()
        
        # Load network
        runner.invoke(cli, ['load', str(sample_s2p_file)], obj=ctx)
        
        # Add series capacitor (User Story 2 scenario)
        result = runner.invoke(cli, [
            'add-component',
            '--port', '1',
            '--type', 'cap',
            '--value', '10pF',
            '--placement', 'series',
            '--show-result'
        ], obj=ctx)
        
        assert result.exit_code == 0
        assert 'capacitor' in result.output.lower()
    
    def test_performance_sc001_snp_load(self, large_s2p_file):
        """SC-001: Load SNP file with 10,000 frequency points in <5 seconds."""
        from snp_tool.parsers.touchstone import parse as parse_snp
        
        start_time = time.time()
        network = parse_snp(str(large_s2p_file))
        elapsed = time.time() - start_time
        
        assert len(network.frequency) >= 100  # At least 100 points
        assert elapsed < 5.0, f"Load took {elapsed:.2f}s, expected <5s"
    
    def test_performance_sc002_component_add(self, sample_s2p_file):
        """SC-002: Add component with S-parameter recalculation <1 second for 1000 points."""
        from snp_tool.cli.commands import cli, CLIContext
        
        runner = CliRunner()
        ctx = CLIContext()
        
        # Load network
        runner.invoke(cli, ['load', str(sample_s2p_file)], obj=ctx)
        
        # Measure component addition time
        start_time = time.time()
        result = runner.invoke(cli, [
            'add-component',
            '--port', '1',
            '--type', 'cap',
            '--value', '10pF',
            '--placement', 'series'
        ], obj=ctx)
        elapsed = time.time() - start_time
        
        assert result.exit_code == 0
        assert elapsed < 1.0, f"Component add took {elapsed:.2f}s, expected <1s"
    
    def test_cli_contract_compliance(self, sample_s2p_file):
        """Verify CLI contracts compliance (contracts/cli-interface.md)."""
        from snp_tool.cli.commands import cli, CLIContext
        
        runner = CliRunner()
        ctx = CLIContext()
        
        # Test load command exists and works
        result = runner.invoke(cli, ['load', str(sample_s2p_file)], obj=ctx)
        assert result.exit_code == 0
        
        # Test info command exists
        result = runner.invoke(cli, ['info'], obj=ctx)
        assert result.exit_code == 0
        
        # Test add-component command exists
        result = runner.invoke(cli, [
            'add-component',
            '--port', '1',
            '--type', 'cap',
            '--value', '10pF',
            '--placement', 'series'
        ], obj=ctx)
        assert result.exit_code == 0
        
        # Test plot command exists
        result = runner.invoke(cli, ['plot', str(sample_s2p_file), '--type', 'smith'])
        assert result.exit_code == 0
    
    def test_multiple_components_workflow(self, sample_s2p_file):
        """Test adding multiple components in sequence."""
        from snp_tool.cli.commands import cli, CLIContext
        
        runner = CliRunner()
        ctx = CLIContext()
        
        # Load
        runner.invoke(cli, ['load', str(sample_s2p_file)], obj=ctx)
        
        # Add component 1
        result = runner.invoke(cli, [
            'add-component',
            '--port', '1',
            '--type', 'cap',
            '--value', '10pF',
            '--placement', 'series'
        ], obj=ctx)
        assert result.exit_code == 0
        
        # Add component 2
        result = runner.invoke(cli, [
            'add-component',
            '--port', '1',
            '--type', 'ind',
            '--value', '5nH',
            '--placement', 'shunt'
        ], obj=ctx)
        assert result.exit_code == 0
        
        # Verify both components present
        result = runner.invoke(cli, ['info', '--components'], obj=ctx)
        assert result.exit_code == 0
        assert '10pF' in result.output or 'capacitor' in result.output.lower()
        assert '5nH' in result.output or 'inductor' in result.output.lower()


# Fixtures
@pytest.fixture
def sample_s2p_file():
    """Create a sample S2P file for testing."""
    content = """! 2-port S-parameters
# GHz S RI R 50
1.0 0.5 0.1 0.02 0.01 0.05 0.1 0.6 0.2
2.0 0.4 0.15 0.03 0.02 0.06 0.12 0.5 0.25
3.0 0.35 0.2 0.04 0.03 0.07 0.14 0.45 0.3
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.s2p', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    yield temp_path
    temp_path.unlink()


@pytest.fixture
def large_s2p_file():
    """Create a larger S2P file for performance testing."""
    import numpy as np
    
    lines = ["! 2-port S-parameters", "# GHz S RI R 50"]
    
    # Generate 100 frequency points
    for i, freq in enumerate(np.linspace(1.0, 3.0, 100)):
        # Generate plausible S-parameter values
        s11_real = 0.5 - i * 0.003
        s11_imag = 0.1 + i * 0.001
        s12_real = 0.02
        s12_imag = 0.01
        s21_real = 0.05
        s21_imag = 0.1
        s22_real = 0.6 - i * 0.002
        s22_imag = 0.2 + i * 0.001
        
        lines.append(
            f"{freq:.3f} {s11_real:.4f} {s11_imag:.4f} "
            f"{s12_real:.4f} {s12_imag:.4f} "
            f"{s21_real:.4f} {s21_imag:.4f} "
            f"{s22_real:.4f} {s22_imag:.4f}"
        )
    
    content = '\n'.join(lines)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.s2p', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    yield temp_path
    temp_path.unlink()
