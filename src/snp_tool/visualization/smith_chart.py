"""Smith Chart visualization module.

Per contracts/smith-chart.md: Smith Chart rendering with matplotlib.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from numpy.typing import NDArray
from typing import Optional, Tuple, List

from snp_tool.models.snp_file import SNPFile
from snp_tool.models.matching_network import MatchingNetwork


def impedance_to_gamma(
    impedance: complex | NDArray[np.complex128], z0: float = 50.0
) -> complex | NDArray[np.complex128]:
    """Convert impedance to reflection coefficient (Gamma).

    Γ = (Z - Z0) / (Z + Z0)

    Args:
        impedance: Complex impedance
        z0: Reference impedance (default 50Ω)

    Returns:
        Complex reflection coefficient
    """
    return (impedance - z0) / (impedance + z0)


def gamma_to_impedance(
    gamma: complex | NDArray[np.complex128], z0: float = 50.0
) -> complex | NDArray[np.complex128]:
    """Convert reflection coefficient to impedance.

    Z = Z0 * (1 + Γ) / (1 - Γ)

    Args:
        gamma: Complex reflection coefficient
        z0: Reference impedance (default 50Ω)

    Returns:
        Complex impedance
    """
    return z0 * (1 + gamma) / (1 - gamma)


def draw_smith_chart_grid(ax: Axes, num_circles: int = 7) -> None:
    """Draw Smith Chart grid lines (constant resistance and reactance circles).

    Args:
        ax: Matplotlib axes
        num_circles: Number of circles for grid
    """
    # Draw unit circle (|Γ| = 1)
    theta = np.linspace(0, 2 * np.pi, 100)
    ax.plot(np.cos(theta), np.sin(theta), "k-", linewidth=1.0)

    # Constant resistance circles
    r_values = [0, 0.2, 0.5, 1.0, 2.0, 5.0]
    for r in r_values:
        # Center and radius of constant-r circle
        center_x = r / (r + 1)
        radius = 1 / (r + 1)

        # Draw circle
        circle_theta = np.linspace(0, 2 * np.pi, 100)
        x = center_x + radius * np.cos(circle_theta)
        y = radius * np.sin(circle_theta)

        # Clip to unit circle
        mask = x**2 + y**2 <= 1.01
        ax.plot(x[mask], y[mask], "gray", linewidth=0.5, alpha=0.5)

    # Constant reactance arcs (positive and negative)
    x_values = [0.2, 0.5, 1.0, 2.0, 5.0]
    for x in x_values:
        # Center and radius of constant-x circle
        center_y = 1 / x
        radius = 1 / x

        # Upper half (positive reactance)
        circle_theta = np.linspace(-np.pi / 2, np.pi / 2, 100)
        cx = 1 + radius * np.cos(circle_theta)
        cy = center_y + radius * np.sin(circle_theta)
        mask = cx**2 + cy**2 <= 1.01
        ax.plot(cx[mask], cy[mask], "gray", linewidth=0.5, alpha=0.5)

        # Lower half (negative reactance)
        cy = -center_y + radius * np.sin(circle_theta)
        mask = cx**2 + cy**2 <= 1.01
        ax.plot(cx[mask], cy[mask], "gray", linewidth=0.5, alpha=0.5)

    # Draw horizontal axis (real axis)
    ax.axhline(y=0, color="gray", linewidth=0.5, alpha=0.7)

    # Add center point marker (50Ω)
    ax.plot(0, 0, "k+", markersize=10, markeredgewidth=1)


class SmithChartPlotter:
    """Smith Chart plotter for RF impedance visualization."""

    def __init__(self, reference_impedance: float = 50.0, figsize: Tuple[int, int] = (8, 8)):
        """Initialize Smith Chart plotter.

        Args:
            reference_impedance: Reference impedance Z0 (default 50Ω)
            figsize: Figure size in inches
        """
        self.z0 = reference_impedance
        self.figsize = figsize

    def create_figure(self) -> Tuple[Figure, Axes]:
        """Create a new Smith Chart figure.

        Returns:
            Tuple of (Figure, Axes)
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        ax.set_aspect("equal")
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.axis("off")

        # Draw grid
        draw_smith_chart_grid(ax)

        return fig, ax

    def plot_impedance_trajectory(
        self,
        snp_file: SNPFile,
        ax: Optional[Axes] = None,
        color: str = "blue",
        label: Optional[str] = None,
        show_markers: bool = True,
        colormap: Optional[str] = None,
    ) -> Tuple[Figure, Axes]:
        """Plot impedance trajectory on Smith Chart.

        Args:
            snp_file: SNP file with impedance data
            ax: Optional existing axes (creates new if None)
            color: Line color (ignored if colormap specified)
            label: Legend label
            show_markers: Whether to show frequency markers
            colormap: Optional colormap name for frequency coloring

        Returns:
            Tuple of (Figure, Axes)
        """
        if ax is None:
            fig, ax = self.create_figure()
        else:
            fig = ax.figure

        # Get impedance trajectory
        frequencies = snp_file.frequency
        impedances = snp_file.get_impedance_trajectory()

        # Convert to Gamma
        gammas = impedance_to_gamma(impedances, self.z0)
        x = np.real(gammas)
        y = np.imag(gammas)

        if colormap:
            # Frequency-colored trajectory
            self._plot_frequency_colored(ax, x, y, frequencies, colormap, label)
        else:
            # Single color trajectory
            ax.plot(x, y, color=color, linewidth=2, label=label)

        if show_markers:
            # Mark start (low freq) and end (high freq)
            ax.plot(x[0], y[0], "o", color="green", markersize=8, label="Start (low f)")
            ax.plot(x[-1], y[-1], "s", color="red", markersize=8, label="End (high f)")

            # Mark center frequency
            center_idx = len(frequencies) // 2
            ax.plot(
                x[center_idx],
                y[center_idx],
                "^",
                color="orange",
                markersize=8,
                label=f"Center ({frequencies[center_idx]/1e9:.2f} GHz)",
            )

        return fig, ax

    def _plot_frequency_colored(
        self,
        ax: Axes,
        x: NDArray[np.float64],
        y: NDArray[np.float64],
        frequencies: NDArray[np.float64],
        colormap: str,
        label: Optional[str],
    ) -> None:
        """Plot trajectory with frequency color gradient.

        Args:
            ax: Matplotlib axes
            x: X coordinates (real part of Gamma)
            y: Y coordinates (imaginary part of Gamma)
            frequencies: Frequency array
            colormap: Colormap name
            label: Legend label
        """
        # Create line segments
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        # Normalize frequencies for coloring
        norm = Normalize(vmin=frequencies.min(), vmax=frequencies.max())
        cmap = plt.get_cmap(colormap)

        # Create colored line collection
        lc = LineCollection(segments, cmap=cmap, norm=norm)
        lc.set_array(frequencies[:-1])
        lc.set_linewidth(2)
        if label:
            lc.set_label(label)

        ax.add_collection(lc)

        # Add colorbar
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, label="Frequency (Hz)", shrink=0.8)
        cbar.ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f"{x/1e9:.2f} GHz")
        )

    def plot_comparison(
        self,
        before: SNPFile,
        after: MatchingNetwork,
        ax: Optional[Axes] = None,
    ) -> Tuple[Figure, Axes]:
        """Plot before/after comparison on Smith Chart.

        Args:
            before: Original device SNP file
            after: Matching network with cascaded S-parameters
            ax: Optional existing axes

        Returns:
            Tuple of (Figure, Axes)
        """
        if ax is None:
            fig, ax = self.create_figure()
        else:
            fig = ax.figure

        # Plot original trajectory
        self.plot_impedance_trajectory(
            before, ax=ax, color="blue", label="Before (Original)", show_markers=False
        )

        # Plot matched trajectory
        frequencies = after.frequency
        if frequencies is not None and after.cascaded_s_parameters is not None:
            s11 = after.cascaded_s_parameters.get("s11")
            if s11 is not None:
                # Convert S11 to impedance
                impedances = self.z0 * (1 + s11) / (1 - s11)
                gammas = impedance_to_gamma(impedances, self.z0)

                x = np.real(gammas)
                y = np.imag(gammas)

                ax.plot(x, y, color="red", linewidth=2, label="After (Matched)", linestyle="--")

                # Mark improvements
                ax.plot(x[0], y[0], "o", color="green", markersize=6)
                ax.plot(x[-1], y[-1], "s", color="darkred", markersize=6)

        ax.legend(loc="upper right")

        return fig, ax

    def plot_point(
        self,
        impedance: complex,
        ax: Optional[Axes] = None,
        color: str = "red",
        marker: str = "o",
        size: int = 10,
        label: Optional[str] = None,
    ) -> Tuple[Figure, Axes]:
        """Plot a single impedance point on Smith Chart.

        Args:
            impedance: Complex impedance value
            ax: Optional existing axes
            color: Marker color
            marker: Marker style
            size: Marker size
            label: Optional label

        Returns:
            Tuple of (Figure, Axes)
        """
        if ax is None:
            fig, ax = self.create_figure()
        else:
            fig = ax.figure

        gamma = impedance_to_gamma(impedance, self.z0)
        ax.plot(np.real(gamma), np.imag(gamma), marker, color=color, markersize=size, label=label)

        return fig, ax

    def save(self, fig: Figure, path: str, dpi: int = 150) -> None:
        """Save Smith Chart figure to file.

        Args:
            fig: Matplotlib figure
            path: Output file path
            dpi: Resolution in dots per inch
        """
        fig.savefig(path, dpi=dpi, bbox_inches="tight")


def plot_smith_chart(
    snp_file: SNPFile,
    title: str = "Smith Chart",
    colormap: str = "viridis",
    save_path: Optional[str] = None,
) -> Figure:
    """Convenience function to plot Smith Chart.

    Args:
        snp_file: SNP file with impedance data
        title: Chart title
        colormap: Colormap for frequency coloring
        save_path: Optional path to save figure

    Returns:
        Matplotlib Figure
    """
    plotter = SmithChartPlotter()
    fig, ax = plotter.plot_impedance_trajectory(
        snp_file, colormap=colormap, show_markers=True
    )

    ax.set_title(title)
    ax.legend(loc="upper right")

    if save_path:
        plotter.save(fig, save_path)

    return fig
