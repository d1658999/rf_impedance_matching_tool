"""Tests for Smith Chart visualization widget.

T044: Write test for Smith Chart widget
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from snp_tool.visualization.smith_chart import (
    SmithChartPlotter,
    impedance_to_gamma,
    gamma_to_impedance,
    plot_smith_chart,
    draw_smith_chart_grid,
)
from snp_tool.models.snp_file import SNPFile


class TestImpedanceToGamma:
    """Test impedance to reflection coefficient conversion."""

    def test_matched_impedance(self):
        """50Ω impedance gives Γ = 0."""
        gamma = impedance_to_gamma(50.0, z0=50.0)
        assert abs(gamma) < 1e-10

    def test_open_circuit(self):
        """Very high impedance gives Γ ≈ 1."""
        gamma = impedance_to_gamma(1e10, z0=50.0)
        assert abs(gamma - 1.0) < 1e-6

    def test_short_circuit(self):
        """Zero impedance gives Γ = -1."""
        gamma = impedance_to_gamma(0.0, z0=50.0)
        assert abs(gamma - (-1.0)) < 1e-10

    def test_complex_impedance(self):
        """Complex impedance maps correctly."""
        z = 50 + 50j  # 50Ω with +50Ω reactance
        gamma = impedance_to_gamma(z, z0=50.0)
        # Verify it's in upper half of Smith Chart (positive reactance)
        assert np.imag(gamma) > 0

    def test_array_input(self):
        """Array of impedances converts correctly."""
        z = np.array([50.0, 100.0, 25.0])
        gamma = impedance_to_gamma(z, z0=50.0)
        assert len(gamma) == 3
        assert abs(gamma[0]) < 1e-10  # Matched
        assert np.real(gamma[1]) > 0  # Higher than Z0
        assert np.real(gamma[2]) < 0  # Lower than Z0


class TestGammaToImpedance:
    """Test reflection coefficient to impedance conversion."""

    def test_zero_gamma(self):
        """Γ = 0 gives Z = Z0."""
        z = gamma_to_impedance(0.0, z0=50.0)
        assert abs(z - 50.0) < 1e-10

    def test_roundtrip(self):
        """Converting Z → Γ → Z gives original Z."""
        z_original = 75 + 25j
        gamma = impedance_to_gamma(z_original, z0=50.0)
        z_recovered = gamma_to_impedance(gamma, z0=50.0)
        assert abs(z_recovered - z_original) < 1e-10


class TestSmithChartPlotter:
    """Test SmithChartPlotter class."""

    @pytest.fixture
    def sample_snp(self):
        """Create a sample SNP file for testing."""
        frequencies = np.linspace(2e9, 2.5e9, 51)
        # Create S11 that traces a trajectory on Smith Chart
        s11 = 0.3 * np.exp(1j * np.linspace(0, np.pi, 51))
        s_params = {
            "s11": s11,
            "s12": np.zeros(51, dtype=complex),
            "s21": np.zeros(51, dtype=complex),
            "s22": np.zeros(51, dtype=complex),
        }
        return SNPFile(
            file_path="test.s2p",
            frequency=frequencies,
            s_parameters=s_params,
            num_ports=2,
            reference_impedance=50.0,
        )

    def test_create_figure(self):
        """Test that create_figure returns valid figure and axes."""
        plotter = SmithChartPlotter()
        fig, ax = plotter.create_figure()

        assert fig is not None
        assert ax is not None
        # Check axes limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        assert xlim[0] < -1.0 and xlim[1] > 1.0
        assert ylim[0] < -1.0 and ylim[1] > 1.0

    def test_plot_impedance_trajectory(self, sample_snp):
        """Test plotting impedance trajectory."""
        plotter = SmithChartPlotter()
        fig, ax = plotter.plot_impedance_trajectory(sample_snp)

        assert fig is not None
        # Check that lines were added (grid + trajectory)
        assert len(ax.lines) > 0

    def test_plot_with_colormap(self, sample_snp):
        """Test plotting with frequency colormap."""
        plotter = SmithChartPlotter()
        fig, ax = plotter.plot_impedance_trajectory(
            sample_snp, colormap="viridis"
        )

        assert fig is not None
        # Check that line collection was added
        assert len(ax.collections) > 0

    def test_plot_point(self):
        """Test plotting a single point."""
        plotter = SmithChartPlotter()
        fig, ax = plotter.plot_point(50.0 + 25j, label="Test Point")

        assert fig is not None
        # Point should be in upper half (positive reactance)
        # Check that markers were added
        markers = [line for line in ax.lines if line.get_linestyle() == "None" or len(line.get_xdata()) == 1]
        assert len(markers) >= 1

    def test_reference_impedance_configurable(self):
        """Test that reference impedance can be configured."""
        plotter = SmithChartPlotter(reference_impedance=75.0)
        assert plotter.z0 == 75.0


class TestSmithChartGrid:
    """Test Smith Chart grid drawing."""

    def test_draw_grid(self):
        """Test that grid is drawn without errors."""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.set_aspect("equal")
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)

        # Should not raise
        draw_smith_chart_grid(ax)

        # Check that lines were added (resistance and reactance circles)
        assert len(ax.lines) > 5


class TestPlotSmithChart:
    """Test convenience function."""

    @pytest.fixture
    def sample_snp(self):
        """Create a sample SNP file for testing."""
        frequencies = np.linspace(2e9, 2.5e9, 51)
        s11 = 0.3 * np.exp(1j * np.linspace(0, np.pi, 51))
        s_params = {
            "s11": s11,
            "s12": np.zeros(51, dtype=complex),
            "s21": np.zeros(51, dtype=complex),
            "s22": np.zeros(51, dtype=complex),
        }
        return SNPFile(
            file_path="test.s2p",
            frequency=frequencies,
            s_parameters=s_params,
            num_ports=2,
            reference_impedance=50.0,
        )

    def test_plot_smith_chart_returns_figure(self, sample_snp):
        """Test that convenience function returns a figure."""
        fig = plot_smith_chart(sample_snp, title="Test Chart")
        assert fig is not None

    def test_plot_smith_chart_with_save(self, sample_snp, tmp_path):
        """Test saving Smith Chart to file."""
        save_path = tmp_path / "smith_chart.png"
        fig = plot_smith_chart(sample_snp, save_path=str(save_path))

        assert save_path.exists()
        assert save_path.stat().st_size > 0
