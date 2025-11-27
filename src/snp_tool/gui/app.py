"""PyQt6 main application for RF impedance matching tool.

T047: Create PyQt6 main window - Redesigned for better RF engineer workflow
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional, List

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
        QTabWidget,
        QLineEdit,
        QSpinBox,
        QDoubleSpinBox,
        QSlider,
        QFormLayout,
        QListWidget,
        QListWidgetItem,
        QFrame,
        QToolBar,
        QDockWidget,
        QScrollArea,
        QGridLayout,
        QCheckBox,
        QToolButton,
        QSizePolicy,
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
    from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QPalette, QKeySequence

    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    QMainWindow = object
    QApplication = None

import numpy as np

from snp_tool.parsers.touchstone import parse as parse_touchstone
from snp_tool.parsers.component_library import parse_folder as parse_component_folder
from snp_tool.optimizer.grid_search import GridSearchOptimizer
from snp_tool.models.snp_file import SNPFile
from snp_tool.models.component_library import ComponentLibrary
from snp_tool.utils.engineering import format_engineering_notation


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


class QuickComponentButton(QPushButton if HAS_PYQT6 else object):
    """Quick-add component button with preset values."""
    
    if HAS_PYQT6:
        component_selected = pyqtSignal(str, str, float)  # type, placement, value
    
    def __init__(self, label: str, comp_type: str, placement: str, value: float, parent=None):
        if HAS_PYQT6:
            super().__init__(label, parent)
            self.comp_type = comp_type
            self.placement = placement
            self.value = value
            self.setToolTip(f"Add {placement} {comp_type} ({format_engineering_notation(value, 'F' if comp_type == 'cap' else 'H')})")
            self.clicked.connect(self._emit_selection)
    
    def _emit_selection(self):
        if HAS_PYQT6:
            self.component_selected.emit(self.comp_type, self.placement, self.value)


class ComponentListItem(QWidget if HAS_PYQT6 else object):
    """Widget for displaying a component in the list with remove button."""
    
    if HAS_PYQT6:
        remove_clicked = pyqtSignal(int)
    
    def __init__(self, index: int, comp_type: str, placement: str, value: float, port: int, parent=None):
        if HAS_PYQT6:
            super().__init__(parent)
            self.index = index
            
            layout = QHBoxLayout(self)
            layout.setContentsMargins(4, 2, 4, 2)
            
            # Icon/indicator
            type_label = QLabel("C" if comp_type == "cap" else "L")
            type_label.setFixedWidth(20)
            type_label.setStyleSheet(
                f"background-color: {'#4CAF50' if comp_type == 'cap' else '#2196F3'}; "
                "color: white; font-weight: bold; border-radius: 3px; text-align: center;"
            )
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(type_label)
            
            # Description
            unit = 'F' if comp_type == 'cap' else 'H'
            value_str = format_engineering_notation(value, unit)
            desc = QLabel(f"Port {port}: {placement.title()} {value_str}")
            desc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(desc)
            
            # Remove button
            remove_btn = QToolButton()
            remove_btn.setText("×")
            remove_btn.setFixedSize(20, 20)
            remove_btn.setStyleSheet("color: red; font-weight: bold;")
            remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.index))
            layout.addWidget(remove_btn)


class MainWindow(QMainWindow if HAS_PYQT6 else object):
    """Main application window - Redesigned for intuitive RF workflow."""

    def __init__(self):
        if not HAS_PYQT6:
            raise ImportError("PyQt6 is required for GUI mode. Install with: pip install PyQt6")

        super().__init__()
        self.setWindowTitle("RF Impedance Matching Tool")
        self.setGeometry(100, 100, 1400, 900)

        # State
        self._device: Optional[SNPFile] = None
        self._library: Optional[ComponentLibrary] = None
        self._result = None
        self._worker: Optional[OptimizationWorker] = None
        self._components: List[dict] = []  # Track added components
        
        # Apply modern styling
        self._apply_style()

        # Setup UI
        self._setup_menu()
        self._setup_toolbar()
        self._setup_central_widget()
        self._setup_status_bar()
        
        # Initial state
        self._update_ui_state()

    def _apply_style(self):
        """Apply modern styling to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
            QPushButton.success {
                background-color: #4CAF50;
            }
            QPushButton.success:hover {
                background-color: #388E3C;
            }
            QPushButton.warning {
                background-color: #FF9800;
            }
            QPushButton.danger {
                background-color: #f44336;
            }
            QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #2196F3;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #ddd;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)

    def _setup_menu(self):
        """Setup menu bar with comprehensive options."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_device_action = QAction("&Open Device SNP...", self)
        open_device_action.setShortcut(QKeySequence.StandardKey.Open)
        open_device_action.triggered.connect(self._open_device)
        file_menu.addAction(open_device_action)

        import_library_action = QAction("&Import Component Library...", self)
        import_library_action.setShortcut("Ctrl+I")
        import_library_action.triggered.connect(self._import_library)
        file_menu.addAction(import_library_action)

        file_menu.addSeparator()
        
        # Session management
        save_session_action = QAction("&Save Session...", self)
        save_session_action.setShortcut(QKeySequence.StandardKey.Save)
        save_session_action.triggered.connect(self._save_session)
        file_menu.addAction(save_session_action)
        
        load_session_action = QAction("&Load Session...", self)
        load_session_action.triggered.connect(self._load_session)
        file_menu.addAction(load_session_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Results...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_results)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        clear_components_action = QAction("&Clear All Components", self)
        clear_components_action.setShortcut("Ctrl+Shift+C")
        clear_components_action.triggered.connect(self._clear_components)
        edit_menu.addAction(clear_components_action)
        
        undo_action = QAction("&Undo Last Component", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo_last_component)
        edit_menu.addAction(undo_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        
        self.show_smith_action = QAction("&Smith Chart", self, checkable=True)
        self.show_smith_action.setChecked(True)
        self.show_smith_action.triggered.connect(self._toggle_smith_chart)
        view_menu.addAction(self.show_smith_action)
        
        self.show_rect_action = QAction("&Rectangular Plots", self, checkable=True)
        self.show_rect_action.setChecked(True)
        self.show_rect_action.triggered.connect(self._toggle_rect_plots)
        view_menu.addAction(self.show_rect_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        quick_start_action = QAction("&Quick Start Guide", self)
        quick_start_action.setShortcut("F1")
        quick_start_action.triggered.connect(self._show_quick_start)
        help_menu.addAction(quick_start_action)
        
        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Setup main toolbar with common actions."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Open device button
        open_btn = QAction("📂 Open SNP", self)
        open_btn.setToolTip("Open device SNP file (Ctrl+O)")
        open_btn.triggered.connect(self._open_device)
        toolbar.addAction(open_btn)
        
        # Import library button
        lib_btn = QAction("📚 Library", self)
        lib_btn.setToolTip("Import component library (Ctrl+I)")
        lib_btn.triggered.connect(self._import_library)
        toolbar.addAction(lib_btn)
        
        toolbar.addSeparator()
        
        # Quick optimize button
        self.quick_optimize_btn = QAction("⚡ Quick Optimize", self)
        self.quick_optimize_btn.setToolTip("Run optimization with default settings")
        self.quick_optimize_btn.triggered.connect(self._run_optimization)
        self.quick_optimize_btn.setEnabled(False)
        toolbar.addAction(self.quick_optimize_btn)
        
        toolbar.addSeparator()
        
        # Undo button
        undo_btn = QAction("↩️ Undo", self)
        undo_btn.setToolTip("Undo last component (Ctrl+Z)")
        undo_btn.triggered.connect(self._undo_last_component)
        toolbar.addAction(undo_btn)
        
        # Clear all button
        clear_btn = QAction("🗑️ Clear", self)
        clear_btn.setToolTip("Clear all components")
        clear_btn.triggered.connect(self._clear_components)
        toolbar.addAction(clear_btn)
        
        toolbar.addSeparator()
        
        # Export button
        export_btn = QAction("💾 Export", self)
        export_btn.setToolTip("Export results (Ctrl+E)")
        export_btn.triggered.connect(self._export_results)
        toolbar.addAction(export_btn)

    def _setup_central_widget(self):
        """Setup central widget with improved layout for RF workflow."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ========== LEFT PANEL: Device & Components ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(350)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        # --- Device Info Section ---
        device_group = QGroupBox("📡 Device")
        device_layout = QVBoxLayout(device_group)

        self.device_label = QLabel("No device loaded\n\nClick 'Load SNP' to start")
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.device_label.setMinimumHeight(80)
        device_layout.addWidget(self.device_label)

        load_device_btn = QPushButton("📂 Load Device SNP...")
        load_device_btn.clicked.connect(self._open_device)
        device_layout.addWidget(load_device_btn)

        left_layout.addWidget(device_group)

        # --- Quick Component Add Section ---
        quick_add_group = QGroupBox("⚡ Quick Add Components")
        quick_add_layout = QVBoxLayout(quick_add_group)
        
        # Port selector
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_spinner = QSpinBox()
        self.port_spinner.setRange(1, 4)
        self.port_spinner.setValue(1)
        port_layout.addWidget(self.port_spinner)
        port_layout.addStretch()
        quick_add_layout.addLayout(port_layout)
        
        # Quick add buttons for common values
        quick_add_layout.addWidget(QLabel("Capacitors:"))
        cap_grid = QGridLayout()
        cap_values = [(1e-12, "1pF"), (10e-12, "10pF"), (100e-12, "100pF"), (1e-9, "1nF")]
        for i, (val, label) in enumerate(cap_values):
            btn_s = QPushButton(f"S {label}")
            btn_s.setToolTip(f"Series capacitor {label}")
            btn_s.clicked.connect(lambda checked, v=val: self._quick_add_component("cap", "series", v))
            btn_p = QPushButton(f"P {label}")
            btn_p.setToolTip(f"Shunt capacitor {label}")
            btn_p.clicked.connect(lambda checked, v=val: self._quick_add_component("cap", "shunt", v))
            cap_grid.addWidget(btn_s, i // 2, (i % 2) * 2)
            cap_grid.addWidget(btn_p, i // 2, (i % 2) * 2 + 1)
        quick_add_layout.addLayout(cap_grid)
        
        quick_add_layout.addWidget(QLabel("Inductors:"))
        ind_grid = QGridLayout()
        ind_values = [(1e-9, "1nH"), (10e-9, "10nH"), (100e-9, "100nH"), (1e-6, "1µH")]
        for i, (val, label) in enumerate(ind_values):
            btn_s = QPushButton(f"S {label}")
            btn_s.setToolTip(f"Series inductor {label}")
            btn_s.clicked.connect(lambda checked, v=val: self._quick_add_component("ind", "series", v))
            btn_p = QPushButton(f"P {label}")
            btn_p.setToolTip(f"Shunt inductor {label}")
            btn_p.clicked.connect(lambda checked, v=val: self._quick_add_component("ind", "shunt", v))
            ind_grid.addWidget(btn_s, i // 2, (i % 2) * 2)
            ind_grid.addWidget(btn_p, i // 2, (i % 2) * 2 + 1)
        quick_add_layout.addLayout(ind_grid)
        
        left_layout.addWidget(quick_add_group)

        # --- Custom Component Add Section ---
        custom_add_group = QGroupBox("🔧 Custom Component")
        custom_layout = QFormLayout(custom_add_group)
        
        self.comp_type_combo = QComboBox()
        self.comp_type_combo.addItems(["Capacitor", "Inductor"])
        custom_layout.addRow("Type:", self.comp_type_combo)
        
        self.placement_combo = QComboBox()
        self.placement_combo.addItems(["Series", "Shunt"])
        custom_layout.addRow("Placement:", self.placement_combo)
        
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., 10pF, 2.2nH, 100uH")
        custom_layout.addRow("Value:", self.value_input)
        
        add_custom_btn = QPushButton("➕ Add Component")
        add_custom_btn.setProperty("class", "success")
        add_custom_btn.clicked.connect(self._add_custom_component)
        custom_layout.addRow(add_custom_btn)
        
        left_layout.addWidget(custom_add_group)

        # --- Component List Section ---
        comp_list_group = QGroupBox("📋 Added Components")
        comp_list_layout = QVBoxLayout(comp_list_group)
        
        self.component_list = QListWidget()
        self.component_list.setMinimumHeight(100)
        comp_list_layout.addWidget(self.component_list)
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setProperty("class", "danger")
        clear_btn.clicked.connect(self._clear_components)
        comp_list_layout.addWidget(clear_btn)
        
        left_layout.addWidget(comp_list_group)

        left_layout.addStretch()

        # ========== CENTER PANEL: Visualization ==========
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setSpacing(0)

        # Visualization tabs
        self.viz_tabs = QTabWidget()
        
        # Smith Chart tab
        smith_tab = QWidget()
        smith_layout = QVBoxLayout(smith_tab)
        try:
            from snp_tool.visualization.smith_chart_widget import InteractiveSmithChart
            self.smith_chart = InteractiveSmithChart(self)
            smith_layout.addWidget(self.smith_chart)
        except ImportError:
            self.smith_chart = None
            smith_layout.addWidget(QLabel("Smith Chart visualization unavailable\n\nInstall matplotlib: pip install matplotlib"))
        self.viz_tabs.addTab(smith_tab, "🎯 Smith Chart")
        
        # Rectangular plots tab (VSWR, Return Loss)
        rect_tab = QWidget()
        rect_layout = QVBoxLayout(rect_tab)
        self.rect_plot_label = QLabel("Load a device to view VSWR and Return Loss plots")
        self.rect_plot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rect_layout.addWidget(self.rect_plot_label)
        # TODO: Add actual rectangular plot widget here
        self.viz_tabs.addTab(rect_tab, "📊 VSWR/RL Plots")
        
        # Comparison tab
        compare_tab = QWidget()
        compare_layout = QVBoxLayout(compare_tab)
        self.compare_label = QLabel("Run optimization to compare original vs matched network")
        self.compare_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        compare_layout.addWidget(self.compare_label)
        self.viz_tabs.addTab(compare_tab, "⚖️ Compare")
        
        center_layout.addWidget(self.viz_tabs)

        # ========== RIGHT PANEL: Optimization & Results ==========
        right_panel = QWidget()
        right_panel.setMaximumWidth(350)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        # --- Component Library Section ---
        library_group = QGroupBox("📚 Component Library")
        library_layout = QVBoxLayout(library_group)

        self.library_label = QLabel("No library loaded\n(Optional: for standard values)")
        self.library_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        library_layout.addWidget(self.library_label)

        load_library_btn = QPushButton("📁 Import Library...")
        load_library_btn.clicked.connect(self._import_library)
        library_layout.addWidget(load_library_btn)
        
        # Use standard values checkbox
        self.use_std_values = QCheckBox("Use standard E24 values")
        self.use_std_values.setChecked(False)
        library_layout.addWidget(self.use_std_values)

        right_layout.addWidget(library_group)

        # --- Optimization Settings Section ---
        opt_group = QGroupBox("⚙️ Optimization Settings")
        opt_layout = QFormLayout(opt_group)

        self.topology_combo = QComboBox()
        self.topology_combo.addItems(["L-section", "Pi-section", "T-section", "Auto (best)"])
        opt_layout.addRow("Topology:", self.topology_combo)
        
        self.target_z_input = QLineEdit("50")
        self.target_z_input.setPlaceholderText("Target impedance (Ω)")
        opt_layout.addRow("Target Z (Ω):", self.target_z_input)
        
        # Frequency range
        freq_layout = QHBoxLayout()
        self.freq_start = QLineEdit()
        self.freq_start.setPlaceholderText("Start")
        self.freq_end = QLineEdit()
        self.freq_end.setPlaceholderText("End")
        freq_layout.addWidget(self.freq_start)
        freq_layout.addWidget(QLabel("-"))
        freq_layout.addWidget(self.freq_end)
        freq_layout.addWidget(QLabel("GHz"))
        opt_layout.addRow("Freq Range:", freq_layout)
        
        # Optimization weights
        opt_layout.addRow(QLabel("Optimization Weights:"))
        
        self.weight_rl = QSlider(Qt.Orientation.Horizontal)
        self.weight_rl.setRange(0, 100)
        self.weight_rl.setValue(50)
        opt_layout.addRow("Return Loss:", self.weight_rl)
        
        self.weight_vswr = QSlider(Qt.Orientation.Horizontal)
        self.weight_vswr.setRange(0, 100)
        self.weight_vswr.setValue(30)
        opt_layout.addRow("VSWR:", self.weight_vswr)
        
        self.weight_bw = QSlider(Qt.Orientation.Horizontal)
        self.weight_bw.setRange(0, 100)
        self.weight_bw.setValue(20)
        opt_layout.addRow("Bandwidth:", self.weight_bw)

        right_layout.addWidget(opt_group)

        # --- Optimize Button ---
        self.optimize_btn = QPushButton("🚀 Run Optimization")
        self.optimize_btn.setProperty("class", "success")
        self.optimize_btn.setMinimumHeight(50)
        font = self.optimize_btn.font()
        font.setPointSize(12)
        self.optimize_btn.setFont(font)
        self.optimize_btn.clicked.connect(self._run_optimization)
        self.optimize_btn.setEnabled(False)
        right_layout.addWidget(self.optimize_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        # --- Results Section ---
        results_group = QGroupBox("📈 Results")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.results_table.setRowCount(0)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
        
        # Apply solution button
        self.apply_solution_btn = QPushButton("✅ Apply Best Solution")
        self.apply_solution_btn.setEnabled(False)
        self.apply_solution_btn.clicked.connect(self._apply_solution)
        results_layout.addWidget(self.apply_solution_btn)

        right_layout.addWidget(results_group)

        right_layout.addStretch()

        # ========== MAIN SPLITTER ==========
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700, 300])

        main_layout.addWidget(splitter)

    def _setup_status_bar(self):
        """Setup status bar with extra info."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add permanent widgets to status bar
        self.status_device_label = QLabel("No device")
        self.status_components_label = QLabel("0 components")
        self.status_bar.addPermanentWidget(self.status_device_label)
        self.status_bar.addPermanentWidget(self.status_components_label)
        
        self.status_bar.showMessage("Ready - Load an SNP file to start")

    def _update_ui_state(self):
        """Update UI elements based on current state."""
        has_device = self._device is not None
        has_library = self._library is not None
        has_result = self._result is not None
        
        # Update optimize buttons
        self.optimize_btn.setEnabled(has_device and has_library)
        self.quick_optimize_btn.setEnabled(has_device and has_library)
        
        # Update apply solution button
        self.apply_solution_btn.setEnabled(has_result)
        
        # Update status bar
        if has_device:
            self.status_device_label.setText(f"📡 {Path(self._device_path).name if hasattr(self, '_device_path') else 'Device'}")
        else:
            self.status_device_label.setText("No device")
        
        self.status_components_label.setText(f"📦 {len(self._components)} components")

    def _update_component_list(self):
        """Update the component list widget."""
        self.component_list.clear()
        for i, comp in enumerate(self._components):
            unit = 'F' if comp['type'] == 'cap' else 'H'
            value_str = format_engineering_notation(comp['value'], unit)
            type_str = "C" if comp['type'] == 'cap' else "L"
            item_text = f"{type_str} | Port {comp['port']} | {comp['placement'].title()} | {value_str}"
            
            item = QListWidgetItem(item_text)
            self.component_list.addItem(item)
        
        self._update_ui_state()

    def _quick_add_component(self, comp_type: str, placement: str, value: float):
        """Add component with preset values."""
        if self._device is None:
            QMessageBox.warning(self, "Warning", "Load a device SNP file first")
            return
        
        port = self.port_spinner.value()
        
        # Add to components list
        self._components.append({
            'port': port,
            'type': comp_type,
            'placement': placement,
            'value': value,
        })
        
        self._update_component_list()
        self._update_visualization()
        
        unit = 'F' if comp_type == 'cap' else 'H'
        self.status_bar.showMessage(
            f"Added {placement} {'capacitor' if comp_type == 'cap' else 'inductor'} "
            f"({format_engineering_notation(value, unit)}) to port {port}"
        )

    def _add_custom_component(self):
        """Add component with custom values from input fields."""
        if self._device is None:
            QMessageBox.warning(self, "Warning", "Load a device SNP file first")
            return
        
        value_str = self.value_input.text().strip()
        if not value_str:
            QMessageBox.warning(self, "Warning", "Enter a component value (e.g., 10pF, 2.2nH)")
            return
        
        comp_type = "cap" if self.comp_type_combo.currentText() == "Capacitor" else "ind"
        placement = self.placement_combo.currentText().lower()
        port = self.port_spinner.value()
        
        # Parse value
        try:
            from snp_tool.utils.engineering import parse_engineering_notation
            unit = 'F' if comp_type == 'cap' else 'H'
            value = parse_engineering_notation(value_str, expected_unit=unit)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Value", str(e))
            return
        
        # Add to components list
        self._components.append({
            'port': port,
            'type': comp_type,
            'placement': placement,
            'value': value,
        })
        
        self._update_component_list()
        self._update_visualization()
        
        # Clear input
        self.value_input.clear()
        
        self.status_bar.showMessage(f"Added custom {placement} component to port {port}")

    def _clear_components(self):
        """Clear all components."""
        if not self._components:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Clear",
            f"Remove all {len(self._components)} components?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._components.clear()
            self._update_component_list()
            self._update_visualization()
            self.status_bar.showMessage("All components cleared")

    def _undo_last_component(self):
        """Remove the last added component."""
        if not self._components:
            self.status_bar.showMessage("No components to undo")
            return
        
        removed = self._components.pop()
        self._update_component_list()
        self._update_visualization()
        
        unit = 'F' if removed['type'] == 'cap' else 'H'
        self.status_bar.showMessage(
            f"Removed {removed['placement']} component ({format_engineering_notation(removed['value'], unit)})"
        )

    def _update_visualization(self):
        """Update all visualization widgets with current state."""
        if self._device is None:
            return
        
        # Update Smith Chart
        if self.smith_chart:
            # TODO: Apply components to network and show result
            self.smith_chart.set_data(self._device)

    def _toggle_smith_chart(self, checked: bool):
        """Toggle Smith Chart visibility."""
        self.viz_tabs.setTabVisible(0, checked)

    def _toggle_rect_plots(self, checked: bool):
        """Toggle rectangular plots visibility."""
        self.viz_tabs.setTabVisible(1, checked)

    def _save_session(self):
        """Save current session to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session",
            "",
            "RF Session Files (*.rfsession);;JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        
        try:
            from snp_tool.utils.session_io import save_session
            session_data = {
                'device_path': getattr(self, '_device_path', None),
                'components': self._components,
                'optimization_result': self._result,
            }
            save_session(session_data, file_path)
            self.status_bar.showMessage(f"Session saved to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _load_session(self):
        """Load session from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            "",
            "RF Session Files (*.rfsession);;JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        
        try:
            from snp_tool.utils.session_io import load_session
            session_data = load_session(file_path)
            
            # Restore device
            if session_data.get('device_path'):
                self._device = parse_touchstone(session_data['device_path'])
                self._device_path = session_data['device_path']
            
            # Restore components
            self._components = session_data.get('components', [])
            
            self._update_component_list()
            self._update_visualization()
            self._update_ui_state()
            
            self.status_bar.showMessage(f"Session loaded from {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))

    def _apply_solution(self):
        """Apply the best optimization solution."""
        if self._result is None:
            return
        
        # Apply matching network components
        if hasattr(self._result, 'matching_network') and self._result.matching_network:
            for comp in self._result.matching_network.components:
                self._components.append({
                    'port': comp.port,
                    'type': 'cap' if comp.component_type.name == 'CAPACITOR' else 'ind',
                    'placement': comp.placement.name.lower(),
                    'value': comp.value,
                })
        
        self._update_component_list()
        self._update_visualization()
        self.status_bar.showMessage("Applied optimization solution")

    def _show_quick_start(self):
        """Show quick start guide."""
        QMessageBox.information(
            self,
            "Quick Start Guide",
            "🚀 RF Impedance Matching Tool - Quick Start\n\n"
            "1️⃣ LOAD DEVICE\n"
            "   Click '📂 Load Device SNP...' to open your .s1p/.s2p file\n\n"
            "2️⃣ ADD COMPONENTS (Optional)\n"
            "   Use Quick Add buttons for common values\n"
            "   Or enter custom values in 'Custom Component'\n\n"
            "3️⃣ IMPORT LIBRARY (For Optimization)\n"
            "   Click '📚 Import Library...' to load component models\n\n"
            "4️⃣ OPTIMIZE\n"
            "   Set target impedance and weights\n"
            "   Click '🚀 Run Optimization'\n\n"
            "5️⃣ EXPORT\n"
            "   Export cascaded S-parameters and schematic\n\n"
            "💡 Tips:\n"
            "• Use Ctrl+Z to undo last component\n"
            "• Click on Smith Chart to see frequency info\n"
            "• Drag frequency slider for real-time analysis"
        )

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
            self._device_path = file_path  # Track path for session save
            freq_min = self._device.frequency.min() / 1e9
            freq_max = self._device.frequency.max() / 1e9
            n_points = len(self._device.frequency)

            self.device_label.setText(
                f"📁 {Path(file_path).name}\n\n"
                f"Ports: {self._device.num_ports}\n"
                f"Freq: {freq_min:.3f} - {freq_max:.3f} GHz\n"
                f"Points: {n_points}"
            )
            self.device_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            # Set frequency range defaults
            self.freq_start.setText(f"{freq_min:.3f}")
            self.freq_end.setText(f"{freq_max:.3f}")

            # Update Smith Chart
            if self.smith_chart:
                self.smith_chart.set_data(self._device)

            self._update_ui_state()
            self.status_bar.showMessage(f"✅ Loaded: {file_path}")

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
                f"📁 {Path(folder_path).name}\n\n"
                f"Capacitors: {n_caps}\n"
                f"Inductors: {n_inds}\n"
                f"Total: {len(self._library.components)}"
            )
            self.library_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

            self._update_ui_state()
            self.status_bar.showMessage(f"✅ Imported library: {folder_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import library:\n{str(e)}")

    def _run_optimization(self):
        """Run optimization in background thread."""
        if self._device is None:
            QMessageBox.warning(self, "Warning", "Load a device SNP file first")
            return
        
        if self._library is None:
            QMessageBox.warning(self, "Warning", "Import a component library first")
            return

        topology = self.topology_combo.currentText()
        if topology == "Auto (best)":
            topology = "L-section"  # Default to L-section for auto

        self.optimize_btn.setEnabled(False)
        self.quick_optimize_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_bar.showMessage("🔄 Optimizing... Please wait")

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
        self._update_ui_state()

        # Update results table
        self.results_table.setRowCount(0)
        metrics = [
            ("🎯 Topology", result.topology_selected),
            ("📊 VSWR at Center", f"{result.optimization_metrics.get('vswr_at_center', 0):.3f}"),
            ("📉 Return Loss", f"{result.optimization_metrics.get('return_loss_at_center_dB', 0):.1f} dB"),
            ("🔄 Reflection Coeff.", f"{result.optimization_metrics.get('reflection_coefficient_at_center', 0):.4f}"),
            ("✅ Success", "✓ Yes" if result.success else "✗ No"),
            ("🔢 Iterations", str(result.optimization_metrics.get("grid_search_iterations", 0))),
            ("⏱️ Duration", f"{result.optimization_metrics.get('grid_search_duration_sec', 0):.2f} s"),
        ]

        for name, value in metrics:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(name))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(value)))

        # Update Smith Chart with comparison
        if self.smith_chart and result.matching_network:
            self.smith_chart.set_data(self._device, result.matching_network)
        
        # Switch to compare tab
        self.viz_tabs.setCurrentIndex(2)

        self.status_bar.showMessage("✅ Optimization complete - Click 'Apply Best Solution' to apply")

    def _on_optimization_error(self, error_msg: str):
        """Handle optimization error."""
        self.progress_bar.setVisible(False)
        self._update_ui_state()
        QMessageBox.critical(self, "Optimization Error", f"❌ {error_msg}")
        self.status_bar.showMessage("❌ Optimization failed")

    def _export_results(self):
        """Export optimization results."""
        if self._result is None:
            QMessageBox.warning(self, "Warning", "No optimization results to export.\nRun optimization first.")
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
                "✅ Export Complete",
                f"Results exported successfully:\n\n"
                f"📄 Schematic: {schematic_path}\n\n"
                f"📊 S-Parameters: {s2p_path}",
            )
            self.status_bar.showMessage(f"✅ Results exported to {folder}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"❌ {str(e)}")

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About RF Impedance Matching Tool",
            "🎯 RF Impedance Matching Tool v0.1.0\n\n"
            "A professional tool for optimizing RF impedance\n"
            "matching networks using vendor component design kits.\n\n"
            "✨ Features:\n"
            "• Load Touchstone .snp files (s1p, s2p, s4p)\n"
            "• Import vendor component libraries\n"
            "• Quick-add common component values\n"
            "• Grid search optimization\n"
            "• Interactive Smith Chart visualization\n"
            "• VSWR and Return Loss plots\n"
            "• Session save/load\n"
            "• Export to S2P and schematics\n\n"
            "📧 For support, visit our documentation.\n\n"
            "© 2024 RF Engineering Tools",
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
