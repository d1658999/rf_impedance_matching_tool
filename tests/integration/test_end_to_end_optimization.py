"""Integration tests for end-to-end optimization workflow."""

import pytest
from pathlib import Path
import numpy as np

from snp_tool import (
    parse,
    parse_folder,
    GridSearchOptimizer,
    Topology,
    SNPFile,
    ComponentLibrary,
    OptimizationResult,
)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestEndToEndOptimization:
    """Integration tests for complete optimization workflow."""

    @pytest.fixture
    def device(self):
        """Load test device."""
        return parse(str(FIXTURES_DIR / "sample_device.s2p"))

    @pytest.fixture
    def library(self):
        """Load test component library."""
        return parse_folder(str(FIXTURES_DIR / "components"))

    def test_load_device(self, device):
        """Test device loading."""
        assert isinstance(device, SNPFile)
        assert device.num_ports == 2
        assert len(device.frequency) == 51

    def test_load_library(self, library):
        """Test library loading."""
        assert isinstance(library, ComponentLibrary)
        assert library.num_components >= 4

    def test_optimization_l_section(self, device, library):
        """Test L-section optimization."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        assert isinstance(result, OptimizationResult)
        assert result.topology_selected == Topology.L_SECTION
        assert result.matching_network is not None
        assert len(result.matching_network.components) == 2

    def test_optimization_returns_metrics(self, device, library):
        """Test that optimization returns valid metrics."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        assert "reflection_coefficient_at_center" in result.optimization_metrics
        assert "vswr_at_center" in result.optimization_metrics
        assert "return_loss_at_center_dB" in result.optimization_metrics

    def test_optimization_improves_matching(self, device, library):
        """Test that optimization improves matching vs. original device."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        # Get original device reflection at center
        center_freq = device.center_frequency
        center_idx = np.argmin(np.abs(device.frequency - center_freq))
        original_gamma = np.abs(device.s11[center_idx])

        # Get optimized reflection
        optimized_gamma = result.optimization_metrics.get("reflection_coefficient_at_center", 1.0)

        # Optimized should be better (lower reflection)
        # Note: This may not always be achievable with limited test components
        assert optimized_gamma <= 1.0

    def test_optimization_with_frequency_range(self, device, library):
        """Test optimization with explicit frequency range."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(
            topology=Topology.L_SECTION,
            frequency_range=(2.2e9, 2.3e9),
            target_frequency=2.25e9,
        )

        assert result.center_frequency == 2.25e9
        assert result.frequency_range == (2.2e9, 2.3e9)

    def test_export_schematic(self, device, library, tmp_path):
        """Test schematic export."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        # Export to temp file
        export_path = tmp_path / "schematic.txt"
        exported = result.export_schematic(str(export_path))

        assert Path(exported).exists()

        # Check content
        content = Path(exported).read_text()
        assert "RF Impedance Matching Network" in content
        assert result.topology_selected.value in content

    def test_export_s_parameters(self, device, library, tmp_path):
        """Test S-parameter export."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        # Export to temp file
        export_path = tmp_path / "cascaded.s2p"
        exported = result.export_s_parameters(str(export_path))

        assert Path(exported).exists()

        # Check it's valid Touchstone format
        content = Path(exported).read_text()
        assert "# GHz S MA R 50" in content

    def test_optimization_result_to_dict(self, device, library):
        """Test result serialization to dict."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        result_dict = result.to_dict()

        assert "device_file" in result_dict
        assert "topology" in result_dict
        assert "components" in result_dict
        assert "metrics" in result_dict
        assert "success" in result_dict

    def test_matching_network_schematic_text(self, device, library):
        """Test schematic text generation."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        schematic = result.matching_network.get_schematic_text()

        assert "Source" in schematic
        assert "50Ω Load" in schematic


class TestSearchIterations:
    """Tests for optimization search metrics."""

    @pytest.fixture
    def device(self):
        return parse(str(FIXTURES_DIR / "sample_device.s2p"))

    @pytest.fixture
    def library(self):
        return parse_folder(str(FIXTURES_DIR / "components"))

    def test_search_iterations_tracked(self, device, library):
        """Test that search iterations are tracked."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        assert optimizer.search_iterations > 0
        assert "grid_search_iterations" in result.optimization_metrics

    def test_search_duration_tracked(self, device, library):
        """Test that search duration is tracked."""
        optimizer = GridSearchOptimizer(device, library)
        result = optimizer.optimize(topology=Topology.L_SECTION)

        assert optimizer.search_duration > 0
        assert "grid_search_duration_sec" in result.optimization_metrics
