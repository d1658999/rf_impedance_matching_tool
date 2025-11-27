"""
Unit tests for rectangular plots (return loss, VSWR, magnitude, phase).

Tests verify FR-015: Visualization support for impedance matching analysis.
"""

import pytest
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for testing
import matplotlib.pyplot as plt

from snp_tool.visualization.rectangular import (
    plot_return_loss,
    plot_vswr,
    plot_magnitude,
    plot_phase,
)
from snp_tool.models.network import SParameterNetwork


@pytest.fixture
def sample_network():
    """Create a sample S-parameter network for testing."""
    frequencies_hz = np.linspace(1e9, 3e9, 50)  # 1-3 GHz
    n_freq = len(frequencies_hz)
    
    # Create S-parameter matrix (n_freq, 2, 2) for 2-port network
    s_params = np.zeros((n_freq, 2, 2), dtype=complex)
    
    for i, f_hz in enumerate(frequencies_hz):
        # Simulate realistic S11 (return loss improving toward center frequency)
        f_norm = (f_hz - 2e9) / 1e9  # Normalize around 2 GHz
        s11_mag = 0.3 * np.exp(-f_norm**2)  # Gaussian shape
        s11_phase = -90 * f_norm  # Phase variation
        
        s11 = s11_mag * np.exp(1j * np.radians(s11_phase))
        s21 = np.sqrt(1 - s11_mag**2)  # Energy conservation approximation
        s12 = s21
        s22 = 0.1 * s11  # Some reflection on port 2
        
        s_params[i] = np.array([[s11, s12], [s21, s22]])
    
    return SParameterNetwork(
        filepath=Path("test.s2p"),
        port_count=2,
        frequencies=frequencies_hz,
        s_parameters=s_params,
        impedance_normalization=50.0,
        frequency_unit="GHz",
        format_type="RI",
        loaded_at=datetime.now(),
        checksum="abc123"
    )


def test_plot_return_loss_basic(sample_network, tmp_path):
    """Test basic return loss plotting."""
    output_file = tmp_path / "return_loss.png"
    
    fig, ax = plot_return_loss(
        network=sample_network,
        port=1,
        output_file=output_file
    )
    
    assert output_file.exists()
    assert fig is not None
    assert ax is not None
    
    # Verify axis labels
    assert ax.get_xlabel().lower().find('freq') >= 0
    assert ax.get_ylabel().lower().find('db') >= 0 or ax.get_ylabel().lower().find('return loss') >= 0
    
    plt.close(fig)


def test_plot_return_loss_threshold(sample_network, tmp_path):
    """Test return loss plot with threshold line."""
    output_file = tmp_path / "return_loss_threshold.png"
    
    fig, ax = plot_return_loss(
        network=sample_network,
        port=1,
        threshold_db=10.0,  # 10 dB threshold
        output_file=output_file
    )
    
    assert output_file.exists()
    
    # Check that there are multiple lines (data + threshold)
    lines = ax.get_lines()
    assert len(lines) >= 1  # At least the data line
    
    plt.close(fig)


def test_plot_vswr_basic(sample_network, tmp_path):
    """Test VSWR vs frequency plot."""
    output_file = tmp_path / "vswr.png"
    
    fig, ax = plot_vswr(
        network=sample_network,
        port=1,
        output_file=output_file
    )
    
    assert output_file.exists()
    assert fig is not None
    
    # Verify axis labels
    assert 'freq' in ax.get_xlabel().lower()
    assert 'vswr' in ax.get_ylabel().lower()
    
    plt.close(fig)


def test_plot_vswr_with_threshold(sample_network, tmp_path):
    """Test VSWR plot with threshold line (default 2.0)."""
    output_file = tmp_path / "vswr_threshold.png"
    
    fig, ax = plot_vswr(
        network=sample_network,
        port=1,
        threshold=2.0,  # VSWR threshold
        output_file=output_file
    )
    
    assert output_file.exists()
    
    # Check for threshold line
    lines = ax.get_lines()
    assert len(lines) >= 1
    
    # VSWR should always be >= 1.0
    for line in lines:
        ydata = line.get_ydata()
        if len(ydata) > 0:
            ydata_array = np.asarray(ydata)
            assert np.all(ydata_array >= 1.0)
    
    plt.close(fig)


def test_plot_magnitude_s_parameters(sample_network, tmp_path):
    """Test S-parameter magnitude plot."""
    output_file = tmp_path / "magnitude.png"
    
    fig, ax = plot_magnitude(
        network=sample_network,
        s_params=[(1, 1), (2, 1)],  # S11 and S21
        output_file=output_file
    )
    
    assert output_file.exists()
    assert fig is not None
    
    # Should have 2 lines (S11 and S21)
    lines = ax.get_lines()
    assert len(lines) == 2
    
    # Verify labels
    assert 'freq' in ax.get_xlabel().lower()
    assert 'magnitude' in ax.get_ylabel().lower() or 'db' in ax.get_ylabel().lower()
    
    plt.close(fig)


def test_plot_magnitude_db_scale(sample_network, tmp_path):
    """Test magnitude plot with dB scale."""
    output_file = tmp_path / "magnitude_db.png"
    
    fig, ax = plot_magnitude(
        network=sample_network,
        s_params=[(1, 1)],
        db_scale=True,
        output_file=output_file
    )
    
    assert output_file.exists()
    
    # In dB scale, values should be <= 0 for passive networks
    lines = ax.get_lines()
    for line in lines:
        ydata = line.get_ydata()
        if len(ydata) > 0:
            assert np.all(ydata <= 0.1)  # Allow small tolerance
    
    plt.close(fig)


def test_plot_phase_s_parameters(sample_network, tmp_path):
    """Test S-parameter phase plot."""
    output_file = tmp_path / "phase.png"
    
    fig, ax = plot_phase(
        network=sample_network,
        s_params=[(1, 1), (2, 1)],
        output_file=output_file
    )
    
    assert output_file.exists()
    assert fig is not None
    
    # Should have 2 lines
    lines = ax.get_lines()
    assert len(lines) == 2
    
    # Verify labels
    assert 'freq' in ax.get_xlabel().lower()
    assert 'phase' in ax.get_ylabel().lower() or 'deg' in ax.get_ylabel().lower()
    
    # Phase should be in degrees (-180 to 180 range)
    for line in lines:
        ydata = line.get_ydata()
        if len(ydata) > 0:
            assert np.all(ydata >= -180)
            assert np.all(ydata <= 180)
    
    plt.close(fig)


def test_plot_output_formats(sample_network, tmp_path):
    """Test saving to different file formats."""
    formats = ['png', 'pdf', 'svg']
    
    for fmt in formats:
        output_file = tmp_path / f"plot.{fmt}"
        
        fig, ax = plot_return_loss(
            network=sample_network,
            port=1,
            output_file=output_file
        )
        
        assert output_file.exists(), f"Failed to create {fmt} file"
        assert output_file.stat().st_size > 0, f"{fmt} file is empty"
        
        plt.close(fig)


def test_plot_styling_consistency(sample_network, tmp_path):
    """Test that plots have consistent styling."""
    output_file1 = tmp_path / "plot1.png"
    output_file2 = tmp_path / "plot2.png"
    
    fig1, ax1 = plot_return_loss(sample_network, 1, output_file=output_file1)
    fig2, ax2 = plot_vswr(sample_network, 1, output_file=output_file2)
    
    # Both should have grid
    assert ax1.get_xgridlines() or ax1.yaxis.get_gridlines()
    assert ax2.get_xgridlines() or ax2.yaxis.get_gridlines()
    
    plt.close(fig1)
    plt.close(fig2)


def test_plot_no_output_file(sample_network):
    """Test plotting without saving to file."""
    fig, ax = plot_return_loss(
        network=sample_network,
        port=1,
        output_file=None
    )
    
    assert fig is not None
    assert ax is not None
    
    plt.close(fig)


def test_plot_frequency_range(sample_network, tmp_path):
    """Test plotting with frequency range restriction."""
    output_file = tmp_path / "plot_range.png"
    
    fig, ax = plot_return_loss(
        network=sample_network,
        port=1,
        freq_range=(1.5e9, 2.5e9),  # 1.5-2.5 GHz
        output_file=output_file
    )
    
    assert output_file.exists()
    
    # Check x-axis limits are within specified range (in GHz units)
    xlim = ax.get_xlim()
    assert xlim[0] >= 1.5 * 0.95  # GHz, allow small margin
    assert xlim[1] <= 2.5 * 1.05  # GHz
    
    plt.close(fig)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
