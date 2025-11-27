"""
Rectangular plot functions for RF analysis.

Provides return loss, VSWR, magnitude, and phase plotting for S-parameters.
Implements FR-015: Visualization support.
"""

from typing import Optional, List, Tuple
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.figure

from snp_tool.models.network import SParameterNetwork


def plot_return_loss(
    network: SParameterNetwork,
    port: int,
    threshold_db: Optional[float] = None,
    freq_range: Optional[Tuple[float, float]] = None,
    output_file: Optional[Path] = None
) -> Tuple[matplotlib.figure.Figure, plt.Axes]:
    """
    Plot return loss (dB) vs frequency for a specified port.
    
    Args:
        network: S-parameter network to plot
        port: Port number (1-indexed)
        threshold_db: Optional threshold line to draw (e.g., -10 dB)
        freq_range: Optional (f_min, f_max) in Hz to restrict x-axis
        output_file: Optional file path to save plot
        
    Returns:
        (figure, axes) tuple for further customization
    """
    # Extract frequencies and S-parameters
    frequencies = network.frequencies
    
    # Get S-parameter for the port (e.g., S11 for port 1)
    # s_parameters shape: (n_freq, n_ports, n_ports)
    s_params = network.s_parameters[:, port-1, port-1]
    
    # Calculate return loss in dB (positive values, higher = better)
    # RL = -20*log10(|S11|)
    return_loss_db = -20 * np.log10(np.abs(s_params) + 1e-12)  # Add small value to avoid log(0)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Apply frequency range filter if specified
    if freq_range:
        mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
        frequencies = frequencies[mask]
        return_loss_db = return_loss_db[mask]
    
    # Plot return loss
    ax.plot(frequencies / 1e9, return_loss_db, 'b-', linewidth=2, label=f'S{port}{port} Return Loss')
    
    # Add threshold line if specified
    if threshold_db is not None:
        ax.axhline(y=threshold_db, color='r', linestyle='--', linewidth=1.5, 
                   label=f'{threshold_db} dB Threshold')
    
    # Styling
    ax.set_xlabel('Frequency (GHz)', fontsize=12)
    ax.set_ylabel('Return Loss (dB)', fontsize=12)
    ax.set_title(f'Return Loss - Port {port}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Set y-axis to show better matching (higher values) at top
    ax.invert_yaxis()
    
    fig.tight_layout()
    
    # Save if output file specified
    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
    
    return fig, ax


def plot_vswr(
    network: SParameterNetwork,
    port: int,
    threshold: float = 2.0,
    freq_range: Optional[Tuple[float, float]] = None,
    output_file: Optional[Path] = None
) -> Tuple[matplotlib.figure.Figure, plt.Axes]:
    """
    Plot VSWR vs frequency for a specified port.
    
    Args:
        network: S-parameter network to plot
        port: Port number (1-indexed)
        threshold: VSWR threshold to draw (default 2.0)
        freq_range: Optional (f_min, f_max) in Hz
        output_file: Optional file path to save plot
        
    Returns:
        (figure, axes) tuple
    """
    # Extract frequencies and S-parameters
    frequencies = network.frequencies
    s_params = network.s_parameters[:, port-1, port-1]
    
    # Calculate VSWR from reflection coefficient
    # VSWR = (1 + |Gamma|) / (1 - |Gamma|)
    gamma = np.abs(s_params)
    vswr = (1 + gamma) / (1 - gamma + 1e-12)  # Avoid division by zero
    
    # Clip extreme values for better visualization
    vswr = np.clip(vswr, 1.0, 20.0)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Apply frequency range filter
    if freq_range:
        mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
        frequencies = frequencies[mask]
        vswr = vswr[mask]
    
    # Plot VSWR
    ax.plot(frequencies / 1e9, vswr, 'g-', linewidth=2, label=f'Port {port} VSWR')
    
    # Add threshold line
    ax.axhline(y=threshold, color='r', linestyle='--', linewidth=1.5,
               label=f'VSWR = {threshold} Threshold')
    
    # Styling
    ax.set_xlabel('Frequency (GHz)', fontsize=12)
    ax.set_ylabel('VSWR', fontsize=12)
    ax.set_title(f'Voltage Standing Wave Ratio - Port {port}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_ylim(bottom=1.0)
    
    fig.tight_layout()
    
    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
    
    return fig, ax


def plot_magnitude(
    network: SParameterNetwork,
    s_params: List[Tuple[int, int]],
    db_scale: bool = True,
    freq_range: Optional[Tuple[float, float]] = None,
    output_file: Optional[Path] = None
) -> Tuple[matplotlib.figure.Figure, plt.Axes]:
    """
    Plot S-parameter magnitudes vs frequency.
    
    Args:
        network: S-parameter network
        s_params: List of (row, col) tuples for S-parameters to plot (1-indexed)
                  e.g., [(1, 1), (2, 1)] for S11 and S21
        db_scale: If True, plot in dB; otherwise linear scale
        freq_range: Optional (f_min, f_max) in Hz
        output_file: Optional file path to save
        
    Returns:
        (figure, axes) tuple
    """
    frequencies = network.frequencies
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['b', 'r', 'g', 'm', 'c', 'y', 'k']
    
    for idx, (row, col) in enumerate(s_params):
        # Extract S-parameter
        s_data = network.s_parameters[:, row-1, col-1]
        
        # Calculate magnitude
        magnitude = np.abs(s_data)
        
        if db_scale:
            magnitude_plot = 20 * np.log10(magnitude + 1e-12)
            ylabel = 'Magnitude (dB)'
        else:
            magnitude_plot = magnitude
            ylabel = 'Magnitude'
        
        # Apply frequency filter
        freqs_plot = frequencies
        if freq_range:
            mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
            freqs_plot = frequencies[mask]
            magnitude_plot = magnitude_plot[mask]
        
        # Plot
        color = colors[idx % len(colors)]
        ax.plot(freqs_plot / 1e9, magnitude_plot, color=color, linewidth=2,
                label=f'S{row}{col}')
    
    # Styling
    ax.set_xlabel('Frequency (GHz)', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title('S-Parameter Magnitude', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    fig.tight_layout()
    
    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
    
    return fig, ax


def plot_phase(
    network: SParameterNetwork,
    s_params: List[Tuple[int, int]],
    freq_range: Optional[Tuple[float, float]] = None,
    output_file: Optional[Path] = None
) -> Tuple[matplotlib.figure.Figure, plt.Axes]:
    """
    Plot S-parameter phase vs frequency.
    
    Args:
        network: S-parameter network
        s_params: List of (row, col) tuples for S-parameters (1-indexed)
        freq_range: Optional (f_min, f_max) in Hz
        output_file: Optional file path to save
        
    Returns:
        (figure, axes) tuple
    """
    frequencies = network.frequencies
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['b', 'r', 'g', 'm', 'c', 'y', 'k']
    
    for idx, (row, col) in enumerate(s_params):
        # Extract S-parameter
        s_data = network.s_parameters[:, row-1, col-1]
        
        # Calculate phase in degrees
        phase_deg = np.angle(s_data, deg=True)
        
        # Apply frequency filter
        freqs_plot = frequencies
        if freq_range:
            mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
            freqs_plot = frequencies[mask]
            phase_deg = phase_deg[mask]
        
        # Plot
        color = colors[idx % len(colors)]
        ax.plot(freqs_plot / 1e9, phase_deg, color=color, linewidth=2,
                label=f'S{row}{col}')
    
    # Styling
    ax.set_xlabel('Frequency (GHz)', fontsize=12)
    ax.set_ylabel('Phase (degrees)', fontsize=12)
    ax.set_title('S-Parameter Phase', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_ylim(-180, 180)
    
    fig.tight_layout()
    
    if output_file:
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
    
    return fig, ax
