"""PyQt6 main application for RF impedance matching tool.

T047: Create PyQt6 main window
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QFileDialog,
        QLabel,
        QComboBox,
        QGroupBox,
        QTableWidget,
        QTableWidgetItem,
        QMessageBox,
        QSplitter,
        QStatusBar,
        QMenuBar,
        QMenu,
        QProgressBar,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QAction

    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    QMainWindow = object
    QApplication = None

import numpy as np

from snp_tool.parsers.touchstone import parse_touchstone
from snp_tool.parsers.component_library import parse_component_folder
from snp_tool.optimizer.grid_search import GridSearchOptimizer
from snp_tool.models.snp_file import SNPFile
from snp_tool.models.component_library import ComponentLibrary


def check_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    return HAS_PYQT6


class OptimizationWorker(QThread if HAS_PYQT6 else object):
    """Background worker for optimization."""

    if HAS_PYQT6:
        finished = pyqtSignal(object)
        error = pyqtSignal(str)
        progress = pyqtSignal(int)

    def __init__(
        self,
        device: SNPFile,
        library: ComponentLibrary,
        topology: str,
        parent: Optional[QWidget] = None,
    ):
        if HAS_PYQT6:
            super().__init__(parent)
        self.device = device
        self.library = library
        self.topology = topology

    def run(self):
        """Run optimization in background."""
        try:
            optimizer = GridSearchOptimizer(self.device, self.library)
            result = optimizer.optimize(topology=self.topology)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow if HAS_PYQT6 else object):
    """Main application window."""

    def __init__(self):
        if not HAS_PYQT6:
            raise ImportError("PyQt6 is required for GUI mode. Install with: pip install PyQt6")

        super().__init__()
        self.setWindowTitle("RF Impedance Matching Tool")
        self.setGeometry(100, 100, 1200, 800)

        # State
        self._device: Optional[SNPFile] = None
        self._library: Optional[ComponentLibrary] = None
        self._result = None
        self._worker: Optional[OptimizationWorker] = None

        # Setup UI
        self._setup_menu()
        self._setup_central_widget()
        self._setup_status_bar()

    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_device_action = QAction("&Open Device SNP...", self)
        open_device_action.setShortcut("Ctrl+O")
        open_device_action.triggered.connect(self._open_device)
        file_menu.addAction(open_device_action)

        import_library_action = QAction("&Import Component Library...", self)
        import_library_action.setShortcut("Ctrl+I")
        import_library_action.triggered.connect(self._import_library)
        file_menu.addAction(import_library_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Results...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_results)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_central_widget(self):
        """Setup central widget with splitter layout."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        # Left panel: Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Device info group
        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout(device_group)

        self.device_label = QLabel("No device loaded")
        device_layout.addWidget(self.device_label)

        load_device_btn = QPushButton("Load Device SNP...")
        load_device_btn.clicked.connect(self._open_device)
        device_layout.addWidget(load_device_btn)

        left_layout.addWidget(device_group)

        # Component library group
        library_group = QGroupBox("Component Library")
        library_layout = QVBoxLayout(library_group)

        self.library_label = QLabel("No library loaded")
        library_layout.addWidget(self.library_label)

        load_library_btn = QPushButton("Import Library...")
        load_library_btn.clicked.connect(self._import_library)
        library_layout.addWidget(load_library_btn)

        left_layout.addWidget(library_group)

        # Optimization group
        opt_group = QGroupBox("Optimization")
        opt_layout = QVBoxLayout(opt_group)

        opt_layout.addWidget(QLabel("Topology:"))
        self.topology_combo = QComboBox()
        self.topology_combo.addItems(["L-section", "Pi-section", "T-section"])
        opt_layout.addWidget(self.topology_combo)

        self.optimize_btn = QPushButton("Optimize")
        self.optimize_btn.clicked.connect(self._run_optimization)
        self.optimize_btn.setEnabled(False)
        opt_layout.addWidget(self.optimize_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        opt_layout.addWidget(self.progress_bar)

        left_layout.addWidget(opt_group)

        # Results group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.results_table.setRowCount(0)
        results_layout.addWidget(self.results_table)

        left_layout.addWidget(results_group)

        left_layout.addStretch()

        # Right panel: Smith Chart
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        right_layout.addWidget(QLabel("Smith Chart"))

        # Import Smith Chart widget
        try:
            from snp_tool.visualization.smith_chart_widget import InteractiveSmithChart
            self.smith_chart = InteractiveSmithChart(self)
            right_layout.addWidget(self.smith_chart)
        except ImportError:
            self.smith_chart = None
            right_layout.addWidget(QLabel("Smith Chart visualization unavailable"))

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        layout.addWidget(splitter)

    def _setup_status_bar(self):
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _open_device(self):
        """Open device SNP file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Device SNP File",
            "",
            "Touchstone Files (*.s1p *.s2p *.s3p *.s4p *.snp);;All Files (*)",
        )
        if not file_path:
            return

        try:
            self._device = parse_touchstone(file_path)
            freq_min = self._device.frequency.min() / 1e9
            freq_max = self._device.frequency.max() / 1e9
            n_points = len(self._device.frequency)

            self.device_label.setText(
                f"{Path(file_path).name}\n"
                f"Ports: {self._device.num_ports}\n"
                f"Freq: {freq_min:.2f} - {freq_max:.2f} GHz\n"
                f"Points: {n_points}"
            )

            # Update Smith Chart
            if self.smith_chart:
                self.smith_chart.set_data(self._device)

            self._update_optimize_button()
            self.status_bar.showMessage(f"Loaded: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load device:\n{str(e)}")

    def _import_library(self):
        """Import component library folder."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Component Library Folder"
        )
        if not folder_path:
            return

        try:
            self._library = parse_component_folder(folder_path)
            n_caps = len(self._library.get_capacitors())
            n_inds = len(self._library.get_inductors())

            self.library_label.setText(
                f"{Path(folder_path).name}\n"
                f"Capacitors: {n_caps}\n"
                f"Inductors: {n_inds}\n"
                f"Total: {len(self._library.components)}"
            )

            self._update_optimize_button()
            self.status_bar.showMessage(f"Imported library: {folder_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import library:\n{str(e)}")

    def _update_optimize_button(self):
        """Enable/disable optimize button based on state."""
        self.optimize_btn.setEnabled(
            self._device is not None and self._library is not None
        )

    def _run_optimization(self):
        """Run optimization in background thread."""
        if self._device is None or self._library is None:
            return

        topology = self.topology_combo.currentText()

        self.optimize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_bar.showMessage("Optimizing...")

        self._worker = OptimizationWorker(
            self._device, self._library, topology, self
        )
        self._worker.finished.connect(self._on_optimization_finished)
        self._worker.error.connect(self._on_optimization_error)
        self._worker.start()

    def _on_optimization_finished(self, result):
        """Handle optimization completion."""
        self._result = result
        self.progress_bar.setVisible(False)
        self.optimize_btn.setEnabled(True)

        # Update results table
        self.results_table.setRowCount(0)
        metrics = [
            ("Topology", result.topology_selected),
            ("VSWR at Center", f"{result.optimization_metrics.get('vswr_at_center', 0):.3f}"),
            ("Return Loss", f"{result.optimization_metrics.get('return_loss_at_center_dB', 0):.1f} dB"),
            ("Reflection Coeff.", f"{result.optimization_metrics.get('reflection_coefficient_at_center', 0):.4f}"),
            ("Success", "✓" if result.success else "✗"),
            ("Iterations", str(result.optimization_metrics.get("grid_search_iterations", 0))),
            ("Duration", f"{result.optimization_metrics.get('grid_search_duration_sec', 0):.2f} s"),
        ]

        for name, value in metrics:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(name))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(value)))

        # Update Smith Chart with comparison
        if self.smith_chart and result.matching_network:
            self.smith_chart.set_data(self._device, result.matching_network)

        self.status_bar.showMessage("Optimization complete")

    def _on_optimization_error(self, error_msg: str):
        """Handle optimization error."""
        self.progress_bar.setVisible(False)
        self.optimize_btn.setEnabled(True)
        QMessageBox.critical(self, "Optimization Error", error_msg)
        self.status_bar.showMessage("Optimization failed")

    def _export_results(self):
        """Export optimization results."""
        if self._result is None:
            QMessageBox.warning(self, "Warning", "No results to export")
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return

        try:
            # Export schematic
            schematic_path = os.path.join(folder, "matching_network_schematic.txt")
            self._result.export_schematic(schematic_path)

            # Export S-parameters
            s2p_path = os.path.join(folder, "cascaded_device.s2p")
            self._result.export_s_parameters(s2p_path)

            QMessageBox.information(
                self,
                "Export Complete",
                f"Results exported to:\n{schematic_path}\n{s2p_path}",
            )
            self.status_bar.showMessage(f"Results exported to {folder}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About RF Impedance Matching Tool",
            "RF Impedance Matching Tool v0.1.0\n\n"
            "A tool for optimizing RF impedance matching networks\n"
            "using vendor component design kits.\n\n"
            "Features:\n"
            "• Load Touchstone .snp files\n"
            "• Import vendor component libraries\n"
            "• Grid search optimization\n"
            "• Interactive Smith Chart visualization",
        )


def run_gui():
    """Run the GUI application."""
    if not HAS_PYQT6:
        print("Error: PyQt6 is required for GUI mode.")
        print("Install with: pip install PyQt6")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
