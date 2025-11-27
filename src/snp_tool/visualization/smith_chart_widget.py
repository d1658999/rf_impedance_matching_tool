"""Interactive Smith Chart widget using matplotlib embedded in PyQt6.

T046: Implement interactive Smith Chart widget
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Callable

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
    from PyQt6.QtCore import pyqtSignal, Qt
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    QWidget = object
    pyqtSignal = lambda *args: None

import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend by default
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from snp_tool.visualization.smith_chart import SmithChartPlotter, impedance_to_gamma
from snp_tool.models.snp_file import SNPFile
from snp_tool.models.matching_network import MatchingNetwork


class SmithChartCanvas(FigureCanvas if HAS_PYQT6 else object):
    """Matplotlib canvas for Smith Chart rendering."""

    def __init__(self, parent: Optional[QWidget] = None, width: int = 6, height: int = 6):
        """Initialize Smith Chart canvas.

        Args:
            parent: Parent widget
            width: Figure width in inches
            height: Figure height in inches
        """
        self.fig = Figure(figsize=(width, height), dpi=100)
        self.ax = self.fig.add_subplot(111)

        if HAS_PYQT6:
            super().__init__(self.fig)
            self.setParent(parent)

        self.plotter = SmithChartPlotter()
        self._snp_file: Optional[SNPFile] = None
        self._comparison: Optional[MatchingNetwork] = None
        self._frequency_cursor_idx: Optional[int] = None

        # Initial draw
        self._draw_grid()

    def _draw_grid(self) -> None:
        """Draw Smith Chart grid."""
        self.ax.clear()
        self.ax.set_aspect("equal")
        self.ax.set_xlim(-1.2, 1.2)
        self.ax.set_ylim(-1.2, 1.2)
        self.ax.axis("off")

        from snp_tool.visualization.smith_chart import draw_smith_chart_grid
        draw_smith_chart_grid(self.ax)

        self.fig.tight_layout()
        self.draw()

    def set_data(
        self,
        snp_file: SNPFile,
        comparison: Optional[MatchingNetwork] = None,
    ) -> None:
        """Set data to display on Smith Chart.

        Args:
            snp_file: SNP file with impedance trajectory
            comparison: Optional matching network for comparison
        """
        self._snp_file = snp_file
        self._comparison = comparison
        self._redraw()

    def _redraw(self) -> None:
        """Redraw the Smith Chart with current data."""
        self._draw_grid()

        if self._snp_file is None:
            return

        if self._comparison:
            self.plotter.plot_comparison(self._snp_file, self._comparison, ax=self.ax)
        else:
            self.plotter.plot_impedance_trajectory(
                self._snp_file,
                ax=self.ax,
                colormap="viridis",
                show_markers=True,
            )

        # Highlight frequency cursor if set
        if self._frequency_cursor_idx is not None:
            self._highlight_frequency(self._frequency_cursor_idx)

        self.ax.legend(loc="upper right", fontsize=8)
        self.fig.tight_layout()
        self.draw()

    def _highlight_frequency(self, freq_idx: int) -> None:
        """Highlight a specific frequency point.

        Args:
            freq_idx: Index into frequency array
        """
        if self._snp_file is None:
            return

        impedances = self._snp_file.get_impedance_trajectory()
        if freq_idx < 0 or freq_idx >= len(impedances):
            return

        z = impedances[freq_idx]
        gamma = impedance_to_gamma(z, self.plotter.z0)

        self.ax.plot(
            np.real(gamma),
            np.imag(gamma),
            "o",
            color="yellow",
            markersize=15,
            markeredgecolor="black",
            markeredgewidth=2,
            zorder=10,
        )

    def set_frequency_index(self, idx: int) -> None:
        """Set the frequency cursor to a specific index.

        Args:
            idx: Index into frequency array
        """
        self._frequency_cursor_idx = idx
        self._redraw()

    def clear(self) -> None:
        """Clear the Smith Chart."""
        self._snp_file = None
        self._comparison = None
        self._frequency_cursor_idx = None
        self._draw_grid()


class InteractiveSmithChart(QWidget if HAS_PYQT6 else object):
    """Interactive Smith Chart widget with frequency cursor.

    Signals:
        frequency_changed: Emitted when frequency cursor changes (frequency_hz, impedance)
    """

    if HAS_PYQT6:
        frequency_changed = pyqtSignal(float, complex)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize interactive Smith Chart.

        Args:
            parent: Parent widget
        """
        if HAS_PYQT6:
            super().__init__(parent)
        else:
            return

        self._snp_file: Optional[SNPFile] = None

        # Layout
        layout = QVBoxLayout(self)

        # Smith Chart canvas
        self.canvas = SmithChartCanvas(self)
        layout.addWidget(self.canvas)

        # Navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        # Frequency info label
        info_layout = QHBoxLayout()
        self.freq_label = QLabel("Frequency: --")
        self.impedance_label = QLabel("Impedance: --")
        self.vswr_label = QLabel("VSWR: --")

        info_layout.addWidget(self.freq_label)
        info_layout.addWidget(self.impedance_label)
        info_layout.addWidget(self.vswr_label)
        layout.addLayout(info_layout)

        # Connect mouse events
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self._on_click)

    def set_data(
        self,
        snp_file: SNPFile,
        comparison: Optional[MatchingNetwork] = None,
    ) -> None:
        """Set data to display.

        Args:
            snp_file: SNP file with impedance trajectory
            comparison: Optional matching network for comparison
        """
        self._snp_file = snp_file
        self.canvas.set_data(snp_file, comparison)
        self._update_info(snp_file.center_frequency)

    def set_frequency(self, freq_hz: float) -> None:
        """Set the frequency cursor.

        Args:
            freq_hz: Frequency in Hz
        """
        if self._snp_file is None:
            return

        # Find nearest frequency index
        idx = np.argmin(np.abs(self._snp_file.frequency - freq_hz))
        self.canvas.set_frequency_index(idx)
        self._update_info(self._snp_file.frequency[idx])

    def _update_info(self, freq_hz: float) -> None:
        """Update frequency info labels.

        Args:
            freq_hz: Current frequency in Hz
        """
        if self._snp_file is None:
            return

        z = self._snp_file.impedance_at_frequency(freq_hz)

        self.freq_label.setText(f"Frequency: {freq_hz/1e9:.3f} GHz")
        self.impedance_label.setText(f"Impedance: {z.real:.1f} + {z.imag:.1f}j Ω")

        # Calculate VSWR
        from snp_tool.optimizer.metrics import vswr
        v = vswr(z, 50.0)
        self.vswr_label.setText(f"VSWR: {v:.2f}")

        if HAS_PYQT6:
            self.frequency_changed.emit(freq_hz, z)

    def _on_mouse_move(self, event) -> None:
        """Handle mouse movement for frequency cursor.

        Args:
            event: Matplotlib mouse event
        """
        if event.inaxes is None or self._snp_file is None:
            return

        # Find nearest point on trajectory
        impedances = self._snp_file.get_impedance_trajectory()
        gammas = impedance_to_gamma(impedances, 50.0)

        x = np.real(gammas)
        y = np.imag(gammas)

        distances = np.sqrt((x - event.xdata) ** 2 + (y - event.ydata) ** 2)
        nearest_idx = np.argmin(distances)

        # Only update if close enough
        if distances[nearest_idx] < 0.15:
            freq = self._snp_file.frequency[nearest_idx]
            self._update_info(freq)

    def _on_click(self, event) -> None:
        """Handle mouse click to set frequency cursor.

        Args:
            event: Matplotlib mouse event
        """
        if event.inaxes is None or self._snp_file is None:
            return

        # Find nearest point
        impedances = self._snp_file.get_impedance_trajectory()
        gammas = impedance_to_gamma(impedances, 50.0)

        x = np.real(gammas)
        y = np.imag(gammas)

        distances = np.sqrt((x - event.xdata) ** 2 + (y - event.ydata) ** 2)
        nearest_idx = np.argmin(distances)

        self.canvas.set_frequency_index(nearest_idx)
        self._update_info(self._snp_file.frequency[nearest_idx])

    def clear(self) -> None:
        """Clear the Smith Chart."""
        self._snp_file = None
        self.canvas.clear()
        self.freq_label.setText("Frequency: --")
        self.impedance_label.setText("Impedance: --")
        self.vswr_label.setText("VSWR: --")
