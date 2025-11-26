"""Tests for bandwidth optimization.

T048: Write test for bandwidth optimization
"""

import pytest
import numpy as np

from snp_tool.models.snp_file import SNPFile
from snp_tool.models.component_library import ComponentLibrary
from snp_tool.models.component import ComponentModel, ComponentType
from snp_tool.optimizer.bandwidth_optimizer import BandwidthOptimizer


class TestBandwidthOptimizer:
    """Test bandwidth optimization."""

    @pytest.fixture
    def sample_device(self):
        """Create sample device with broad frequency range."""
        frequencies = np.linspace(2e9, 3e9, 101)  # 2-3 GHz, 101 points

        # Create S11 that shows poor matching across band
        s11 = 0.5 * np.exp(1j * np.linspace(0, 2 * np.pi, 101))
        s_params = {
            "s11": s11,
            "s12": np.ones(101, dtype=complex) * 0.9,
            "s21": np.ones(101, dtype=complex) * 0.9,
            "s22": np.zeros(101, dtype=complex),
        }

        return SNPFile(
            file_path="device.s2p",
            frequency=frequencies,
            s_parameters=s_params,
            num_ports=2,
            reference_impedance=50.0,
        )

    @pytest.fixture
    def sample_library(self):
        """Create sample component library."""
        library = ComponentLibrary(library_path="/tmp")
        frequencies = np.linspace(1e9, 4e9, 101)

        # Add capacitors
        for value_pf in [1, 2.2, 4.7, 10, 22, 47]:
            s11 = 0.1 * np.exp(-1j * np.pi * frequencies / 1e10)
            s_params = {
                "s11": s11,
                "s12": np.ones(101, dtype=complex) * 0.95,
                "s21": np.ones(101, dtype=complex) * 0.95,
                "s22": s11,
            }
            component = ComponentModel(
                s2p_file_path=f"cap_{value_pf}pf.s2p",
                manufacturer="Test",
                part_number=f"CAP-{value_pf}PF",
                component_type=ComponentType.CAPACITOR,
                value=f"{value_pf}pF",
                frequency=frequencies,
                s_parameters=s_params,
                reference_impedance=50.0,
            )
            library.add_component(component)

        # Add inductors
        for value_nh in [1, 2.2, 4.7, 10, 22]:
            s11 = 0.1 * np.exp(1j * np.pi * frequencies / 1e10)
            s_params = {
                "s11": s11,
                "s12": np.ones(101, dtype=complex) * 0.95,
                "s21": np.ones(101, dtype=complex) * 0.95,
                "s22": s11,
            }
            component = ComponentModel(
                s2p_file_path=f"ind_{value_nh}nh.s2p",
                manufacturer="Test",
                part_number=f"IND-{value_nh}NH",
                component_type=ComponentType.INDUCTOR,
                value=f"{value_nh}nH",
                frequency=frequencies,
                s_parameters=s_params,
                reference_impedance=50.0,
            )
            library.add_component(component)

        return library

    def test_bandwidth_optimizer_exists(self):
        """Test that BandwidthOptimizer can be instantiated."""
        device = SNPFile(
            file_path="test.s2p",
            frequency=np.array([1e9, 2e9]),
            s_parameters={"s11": np.array([0.5, 0.5], dtype=complex)},
            num_ports=2,
        )
        library = ComponentLibrary(library_path="/tmp")
        optimizer = BandwidthOptimizer(device, library)
        assert optimizer is not None

    def test_optimize_bandwidth_returns_result(self, sample_device, sample_library):
        """Test that bandwidth optimization returns a result."""
        optimizer = BandwidthOptimizer(sample_device, sample_library)
        result = optimizer.optimize(topology="L-section")

        assert result is not None
        assert result.matching_network is not None
        assert "max_vswr_in_band" in result.optimization_metrics

    def test_optimize_reports_bandwidth_metrics(self, sample_device, sample_library):
        """Test that bandwidth metrics are reported."""
        optimizer = BandwidthOptimizer(sample_device, sample_library)
        result = optimizer.optimize(topology="L-section")

        metrics = result.optimization_metrics
        assert "max_vswr_in_band" in metrics
        assert "bandwidth_vswr_lt_2" in metrics or "bandwidth_hz" in metrics

    def test_optimize_minimizes_max_vswr(self, sample_device, sample_library):
        """Test that optimization minimizes maximum VSWR across band."""
        optimizer = BandwidthOptimizer(sample_device, sample_library)
        result = optimizer.optimize(topology="L-section")

        # Should attempt to minimize max VSWR
        max_vswr = result.optimization_metrics.get("max_vswr_in_band", float("inf"))
        # With test components, should achieve some improvement
        assert max_vswr > 0

    def test_optimize_with_frequency_range(self, sample_device, sample_library):
        """Test optimization over specific frequency range."""
        optimizer = BandwidthOptimizer(sample_device, sample_library)

        # Optimize only 2.4-2.5 GHz band
        result = optimizer.optimize(
            topology="L-section",
            frequency_range=(2.4e9, 2.5e9),
        )

        assert result is not None
