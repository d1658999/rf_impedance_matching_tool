"""Tests for export functionality (Tasks 3.1.1-3.1.2)."""

import pytest
import json
import csv
from pathlib import Path
from datetime import datetime
import numpy as np
import skrf as rf

from snp_tool.export.snp_export import export_snp, get_export_accuracy
from snp_tool.export.config_export import export_config
from snp_tool.models.component import MatchingComponent, ComponentType, PlacementType
from snp_tool.utils.exceptions import SNPToolError


class TestSNPExport:
    """Test SNP file export functionality (Task 3.1.1)."""
    
    def test_export_cascaded_snp(self, tmp_path):
        """Test export of cascaded S-parameters to SNP file."""
        # Create a simple test network
        freq = rf.Frequency(start=1, stop=2, npoints=101, unit='GHz')
        network = rf.Network(frequency=freq, z0=50)
        network.s = np.random.random((101, 2, 2)) + 1j * np.random.random((101, 2, 2))
        network.s = network.s * 0.5  # Keep passive
        
        output_file = tmp_path / "exported.s2p"
        export_snp(network, output_file)
        
        assert output_file.exists()
        
        # Reload and verify
        reloaded = rf.Network(str(output_file))
        assert reloaded.nports == network.nports
        assert len(reloaded.frequency) == len(network.frequency)
        
    def test_export_accuracy(self, tmp_path):
        """Test export accuracy meets SC-007 requirements (0.1 dB, 1 deg)."""
        freq = rf.Frequency(start=1, stop=2, npoints=101, unit='GHz')
        network = rf.Network(frequency=freq, z0=50)
        # Create deterministic network for accuracy testing
        network.s = np.zeros((101, 2, 2), dtype=complex)
        network.s[:, 0, 0] = 0.1 + 0.2j
        network.s[:, 1, 1] = 0.15 + 0.25j
        network.s[:, 0, 1] = 0.9 + 0.1j
        network.s[:, 1, 0] = 0.9 + 0.1j
        
        output_file = tmp_path / "test_accuracy.s2p"
        export_snp(network, output_file)
        
        reloaded = rf.Network(str(output_file))
        accuracy = get_export_accuracy(network, reloaded)
        
        assert accuracy['meets_sc007'], f"Accuracy check failed: {accuracy}"
        assert accuracy['max_magnitude_error_db'] < 0.1
        assert accuracy['max_phase_error_deg'] < 1.0
        
    def test_export_format_preservation(self, tmp_path):
        """Test that original file format is preserved when format='auto'."""
        freq = rf.Frequency(start=1, stop=2, npoints=51, unit='GHz')
        network = rf.Network(frequency=freq, z0=50)
        network.s = np.random.random((51, 2, 2)) + 1j * np.random.random((51, 2, 2))
        network.s = network.s * 0.5
        
        output_file = tmp_path / "format_test.s2p"
        export_snp(network, output_file, format_type='MA')
        
        # Verify file can be reloaded
        reloaded = rf.Network(str(output_file))
        assert reloaded.nports == 2
        
    def test_export_empty_network_raises_error(self, tmp_path):
        """Test that exporting empty network raises error."""
        network = rf.Network()
        output_file = tmp_path / "empty.s2p"
        
        with pytest.raises(SNPToolError, match="Cannot export empty network"):
            export_snp(network, output_file)
            
    def test_export_invalid_path_raises_error(self):
        """Test that invalid output path raises error."""
        freq = rf.Frequency(start=1, stop=2, npoints=51, unit='GHz')
        network = rf.Network(frequency=freq, z0=50)
        network.s = np.random.random((51, 2, 2)) + 1j * np.random.random((51, 2, 2))
        
        with pytest.raises(SNPToolError):
            export_snp(network, "/nonexistent/path/file.s2p")


class TestConfigExport:
    """Test component configuration export (Task 3.1.2)."""
    
    @pytest.fixture
    def sample_components(self):
        """Create sample components for testing."""
        return [
            MatchingComponent(
                id="comp1",
                port=1,
                component_type=ComponentType.CAPACITOR,
                value=10e-12,  # 10 pF
                placement=PlacementType.SERIES,
                order=0,
                created_at=datetime(2025, 1, 1, 12, 0, 0)
            ),
            MatchingComponent(
                id="comp2",
                port=1,
                component_type=ComponentType.INDUCTOR,
                value=5e-9,  # 5 nH
                placement=PlacementType.SHUNT,
                order=1,
                created_at=datetime(2025, 1, 1, 12, 0, 1)
            )
        ]
    
    def test_export_components_json(self, tmp_path, sample_components):
        """Test export component configuration to JSON."""
        output_file = tmp_path / "config.json"
        export_config(sample_components, output_file, format='json')
        
        assert output_file.exists()
        
        # Verify JSON structure
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert 'metadata' in data
        assert 'components' in data
        assert len(data['components']) == 2
        assert data['components'][0]['type'] == 'capacitor'
        assert data['components'][0]['port'] == 1
        assert data['components'][1]['type'] == 'inductor'
        
    def test_export_components_csv(self, tmp_path, sample_components):
        """Test export component configuration to CSV."""
        output_file = tmp_path / "config.csv"
        export_config(sample_components, output_file, format='csv')
        
        assert output_file.exists()
        
        # Verify CSV content
        with open(output_file, 'r') as f:
            lines = f.readlines()
        
        # Check metadata comments
        assert lines[0].startswith("# Export Date:")
        assert lines[1].startswith("# Tool Version:")
        
        # Check CSV data
        reader = csv.DictReader([line for line in lines if not line.startswith('#')])
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]['type'] == 'capacitor'
        assert rows[1]['type'] == 'inductor'
        
    def test_export_with_metadata(self, tmp_path, sample_components):
        """Test export includes metadata."""
        output_file = tmp_path / "config_meta.json"
        metadata = {
            'source_network': 'test_antenna.s2p',
            'optimization_score': 0.95
        }
        
        export_config(sample_components, output_file, format='json', metadata=metadata)
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert data['metadata']['source_network'] == 'test_antenna.s2p'
        assert data['metadata']['optimization_score'] == 0.95
        assert 'export_date' in data['metadata']
        assert 'tool_version' in data['metadata']
        
    def test_export_unsupported_format_raises_error(self, tmp_path, sample_components):
        """Test that unsupported format raises error."""
        output_file = tmp_path / "config.xml"
        
        with pytest.raises(SNPToolError, match="Unsupported export format"):
            export_config(sample_components, output_file, format='xml')
            
    def test_export_empty_component_list(self, tmp_path):
        """Test export empty component list."""
        output_file = tmp_path / "empty.json"
        export_config([], output_file, format='json')
        
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert len(data['components']) == 0
        assert data['metadata']['component_count'] == 0
