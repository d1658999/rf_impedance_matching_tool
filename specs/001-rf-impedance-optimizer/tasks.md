# Task Decomposition: RF Impedance Matching Optimizer

**Branch**: `001-rf-impedance-optimizer`  
**Date**: 2025-11-27  
**Phase**: 2 (Task Decomposition)

**Input**: plan.md, data-model.md, contracts/

---

## Overview

This document decomposes the RF Impedance Matching Optimizer into implementable tasks following Test-Driven Development (TDD) workflow per constitution.

**Priority**: User Stories from spec.md (P1 = MVP, P2 = Enhancement, P3 = Workflow Support)

---

## Task Organization

Tasks are organized by:
1. **Priority** (P1, P2, P3 from user stories)
2. **Dependency order** (foundation → features → integrations)
3. **TDD workflow** (Test → Implement → Refactor)

---

## P1 Tasks: MVP (Must Have)

### Phase 1.1: Foundation & Core Infrastructure

#### Task 1.1.1: Setup Project Structure & Dependencies

**User Story**: N/A (Infrastructure)  
**Priority**: P1  
**Dependencies**: None  
**Estimated Effort**: 2-4 hours

**TDD Steps**:
1. ✅ Write test: Verify pyproject.toml has correct dependencies
2. Implement: Update pyproject.toml with scipy, python-json-logger
3. Verify: `pip install -e .[all]` succeeds

**Acceptance Criteria**:
- [X] All dependencies from research.md added to pyproject.toml
- [X] Virtual environment installs cleanly
- [X] `snp-tool --version` returns version number
- [X] Pytest runs (even with 0 tests)

**Files**:
- `pyproject.toml` (update dependencies)
- `src/snp_tool/__init__.py` (add __version__)

---

#### Task 1.1.2: Implement Data Models (Entities)

**User Story**: Foundation for all features  
**Priority**: P1  
**Dependencies**: Task 1.1.1  
**Estimated Effort**: 6-8 hours

**TDD Steps**:
1. Write test: `test_sparameter_network_creation()` - create network, verify fields
2. Write test: `test_matching_component_validation()` - test value ranges, port limits
3. Implement: Data classes in `src/snp_tool/models/`
4. Write test: `test_component_value_display()` - engineering notation property
5. Refactor: Add validation methods

**Acceptance Criteria**:
- [X] All 6 entities from data-model.md implemented with type hints
- [X] Validation rules enforced (FR-003: max 5 components, value ranges)
- [X] All entity tests pass (100% coverage on models/)
- [X] Engineering notation display works (`value_display` property)

**Files**:
- `src/snp_tool/models/__init__.py`
- `src/snp_tool/models/network.py` (SParameterNetwork)
- `src/snp_tool/models/component.py` (MatchingComponent, ComponentType, PlacementType)
- `src/snp_tool/models/port_config.py` (PortConfiguration)
- `src/snp_tool/models/frequency.py` (FrequencyPoint)
- `src/snp_tool/models/solution.py` (OptimizationSolution)
- `src/snp_tool/models/session.py` (WorkSession)
- `tests/unit/test_models.py`

---

#### Task 1.1.3: Implement Engineering Notation Parser

**User Story**: Foundation for FR-005 (component value input)  
**Priority**: P1  
**Dependencies**: Task 1.1.1  
**Estimated Effort**: 3-4 hours

**TDD Steps**:
1. Write test: `test_parse_valid_notation()` - "10pF" → 1e-11
2. Write test: `test_parse_invalid_notation()` - raise ValueError with message
3. Implement: regex parser in `src/snp_tool/utils/engineering.py`
4. Write test: `test_format_engineering_notation()` - 1e-11 → "10.00pF"
5. Write test: `test_all_multipliers()` - p, n, u, µ, m, k, M, G
6. Refactor: Edge cases (0pF, 1000000nH)

**Acceptance Criteria**:
- [X] Parses all valid engineering notation (10pF, 2.2nH, 100uH, 1.5GHz)
- [X] Validates unit types (F, H, Hz)
- [X] Handles alternative µ character
- [X] Formats values back to engineering notation
- [X] Detailed error messages for invalid input
- [X] 100% test coverage on engineering.py

**Files**:
- `src/snp_tool/utils/__init__.py`
- `src/snp_tool/utils/engineering.py`
- `tests/unit/test_utils.py` (test_engineering_notation)

---

#### Task 1.1.4: Implement Structured Logging

**User Story**: Foundation for observability (Constitution Principle V)  
**Priority**: P1  
**Dependencies**: Task 1.1.1  
**Estimated Effort**: 2-3 hours

**TDD Steps**:
1. Write test: `test_logger_setup_text_format()` - verify human-readable output
2. Write test: `test_logger_setup_json_format()` - verify JSON structure
3. Implement: `src/snp_tool/utils/logging.py` with setup_logger()
4. Write test: `test_logger_extra_fields()` - verify extra data in JSON logs
5. Integrate: Add logging to future modules

**Acceptance Criteria**:
- [X] Logger supports text and JSON formats
- [X] JSON logs include timestamp, level, message, extra fields
- [X] Logging configurable via log level (DEBUG, INFO, WARNING, ERROR)
- [X] No logging overhead when level=WARNING (performance)
- [X] Tests verify log output format

**Files**:
- `src/snp_tool/utils/logging.py`
- `tests/unit/test_logging.py`

---

### Phase 1.2: SNP Parsing & Validation (User Story 1)

#### Task 1.2.1: Implement SNP File Parser

**User Story**: User Story 1 - Load and Analyze S-Parameter Files  
**Priority**: P1  
**Dependencies**: Task 1.1.2 (data models)  
**Estimated Effort**: 8-10 hours

**TDD Steps**:
1. Write test: `test_parse_valid_s2p()` - load fixture, verify network fields
2. Write test: `test_parse_frequency_units()` - Hz, MHz, GHz normalization
3. Implement: `parse_snp()` wrapping scikit-rf with validation
4. Write test: `test_parse_impedance_normalization()` - 50Ω, 75Ω
5. Write test: `test_parse_format_types()` - RI, MA, DB
6. Write test: `test_performance_large_file()` - 10,000 freq points <5s (SC-001)
7. Refactor: Error handling, checksum calculation

**Acceptance Criteria**:
- [X] Parses S1P, S2P, S4P files successfully
- [X] Handles all Touchstone format variations (RI, MA, DB)
- [X] Normalizes frequency units to Hz internally
- [X] Calculates MD5 checksum for file integrity
- [X] Performance: <5 seconds for 10,000 frequency points (SC-001)
- [X] All parser tests pass

**Files**:
- `src/snp_tool/parsers/__init__.py`
- `src/snp_tool/parsers/touchstone.py`
- `tests/fixtures/snp_files/` (test fixtures: valid_antenna.s2p, filter.s2p)
- `tests/unit/test_parsers.py`
- `tests/performance/test_parser_performance.py`

---

#### Task 1.2.2: Implement SNP File Validator

**User Story**: User Story 1 (FR-012 - detailed validation reports)  
**Priority**: P1  
**Dependencies**: Task 1.2.1  
**Estimated Effort**: 6-8 hours

**TDD Steps**:
1. Write test: `test_validate_valid_file()` - is_valid=True, no errors
2. Write test: `test_validate_missing_frequency()` - error with line number
3. Write test: `test_validate_non_numeric_sparams()` - error with suggested fix
4. Implement: `validate_snp_file()` with ValidationReport
5. Write test: `test_validate_passive_violation()` - |S| > 1.0 detected
6. Write test: `test_validation_report_to_string()` - human-readable format
7. Refactor: Add suggested fixes for common errors

**Acceptance Criteria**:
- [X] Validates frequency monotonicity
- [X] Detects non-numeric values with line numbers
- [X] Detects passive network violations (|S| > 1.0)
- [X] ValidationReport includes line numbers, error types, suggested fixes
- [X] Formats as text and JSON for CLI output
- [X] All validation tests pass

**Files**:
- `src/snp_tool/parsers/validator.py`
- `tests/fixtures/snp_files/` (invalid files for testing)
- `tests/unit/test_validator.py`

---

#### Task 1.2.3: Implement Impedance Calculations

**User Story**: User Story 1 (FR-002, FR-007 - display impedance metrics)  
**Priority**: P1  
**Dependencies**: Task 1.2.1  
**Estimated Effort**: 5-6 hours

**TDD Steps**:
1. Write test: `test_calculate_impedance_from_s11()` - verify Z = z0*(1+S11)/(1-S11)
2. Write test: `test_calculate_vswr()` - from impedance and reflection coeff
3. Implement: `src/snp_tool/core/impedance.py` functions
4. Write test: `test_calculate_return_loss()` - verify RL = -20*log10(|Gamma|)
5. Write test: `test_calculate_bandwidth()` - frequency range meeting threshold
6. Refactor: Handle edge cases (VSWR=1, perfect match)

**Acceptance Criteria**:
- [X] calculate_impedance() matches RF textbook formulas
- [X] VSWR calculation accurate (1.0 = perfect match)
- [X] Return loss in dB (positive values, higher = better)
- [X] Bandwidth calculation finds frequency range meeting threshold
- [X] All impedance calculation tests pass with tolerance (0.01%)

**Files**:
- `src/snp_tool/core/__init__.py`
- `src/snp_tool/core/impedance.py`
- `tests/unit/test_core_impedance.py`

---

### Phase 1.3: Component Addition & Cascading (User Story 2)

#### Task 1.3.1: Implement Component Network Creation

**User Story**: User Story 2 - Add Matching Components  
**Priority**: P1  
**Dependencies**: Task 1.1.2, Task 1.2.1  
**Estimated Effort**: 8-10 hours

**TDD Steps**:
1. Write test: `test_create_series_capacitor()` - verify Z-matrix for capacitor
2. Write test: `test_create_shunt_capacitor()` - verify Y-matrix
3. Implement: Component network creation functions (research.md Section 6)
4. Write test: `test_create_series_inductor()` - verify Z-matrix for inductor
5. Write test: `test_create_shunt_inductor()` - verify Y-matrix
6. Write test: `test_component_impedance_vs_frequency()` - verify reactance scaling
7. Refactor: Vectorized numpy operations for performance

**Acceptance Criteria**:
- [X] Creates 2-port networks for all component types (cap/ind, series/shunt)
- [X] Z-parameters correct for series elements
- [X] Y-parameters correct for shunt elements
- [X] Frequency-dependent impedance accurate
- [X] All component creation tests pass

**Files**:
- `src/snp_tool/core/network_calc.py`
- `tests/unit/test_network_calc.py`

---

#### Task 1.3.2: Implement Component Cascading

**User Story**: User Story 2 (FR-004 - real-time S-parameter recalculation)  
**Priority**: P1  
**Dependencies**: Task 1.3.1  
**Estimated Effort**: 6-8 hours

**TDD Steps**:
1. Write test: `test_add_single_component()` - verify S-parameters updated
2. Write test: `test_cascade_multiple_components()` - order matters
3. Implement: `add_component()` and `apply_multiple_components()`
4. Write test: `test_performance_1000_freq_points()` - <1 second (SC-002, FR-004)
5. Write test: `test_max_5_components_constraint()` - raises ComponentLimitError
6. Refactor: Immutable network operations (return new network)

**Acceptance Criteria**:
- [X] add_component() cascades component to network via ABCD matrices
- [X] S-parameters recalculated correctly
- [X] Multiple components cascade in correct order (order field)
- [X] Performance: <1 second for 1000 frequency points (SC-002)
- [X] Enforces max 5 components per port (FR-003)
- [X] Returns new network (immutable pattern)

**Files**:
- `src/snp_tool/core/network_calc.py` (extend)
- `tests/unit/test_network_calc.py` (extend)
- `tests/performance/test_component_performance.py`

---

#### Task 1.3.3: Implement CLI Load & Add-Component Commands

**User Story**: User Story 1 & 2 (CLI interface)  
**Priority**: P1  
**Dependencies**: Task 1.2.1, Task 1.3.2, Task 1.1.3  
**Estimated Effort**: 8-10 hours

**TDD Steps**:
1. Write test: `test_cli_load_command()` - invoke CLI, check output
2. Write test: `test_cli_load_invalid_file()` - verify exit code 2
3. Implement: CLI commands using click framework
4. Write test: `test_cli_add_component()` - verify component added
5. Write test: `test_cli_json_output()` - JSON format for automation
6. Write test: `test_cli_info_command()` - display network info
7. Refactor: Output formatters (text vs JSON)

**Acceptance Criteria**:
- [X] `snp-tool load` loads SNP file and displays summary
- [X] `snp-tool load --json` outputs JSON format
- [X] `snp-tool load --validate-only` validates without loading
- [X] `snp-tool add-component` adds component with engineering notation
- [X] `snp-tool info` displays network and metrics
- [X] All CLI contract tests pass (contracts/cli-interface.md)
- [X] Exit codes match specification

**Files**:
- `src/snp_tool/cli/__init__.py`
- `src/snp_tool/cli/commands.py`
- `src/snp_tool/cli/output.py` (formatters)
- `src/snp_tool/main.py` (CLI entry point)
- `tests/integration/test_cli_commands.py`

---

#### Task 1.3.4: Implement Controller Layer (Shared CLI/GUI)

**User Story**: Foundation for FR-019 (identical CLI/GUI results)  
**Priority**: P1  
**Dependencies**: Task 1.3.2  
**Estimated Effort**: 4-6 hours

**TDD Steps**:
1. Write test: `test_controller_load_snp()` - verify network loaded
2. Write test: `test_controller_add_component()` - verify component added and S-params updated
3. Implement: `ImpedanceMatchingController` class (research.md Section 7)
4. Write test: `test_controller_shared_by_cli_gui()` - same instance, same results
5. Refactor: Extract business logic from CLI commands

**Acceptance Criteria**:
- [X] Controller manages network state (load, components, optimization)
- [X] All business logic in controller, not CLI commands
- [X] CLI commands thin wrappers around controller methods
- [X] Controller methods have unit tests (independent of CLI/GUI)
- [X] Ready for GUI integration (P2)

**Files**:
- `src/snp_tool/controller.py`
- `tests/unit/test_controller.py`

---

### Phase 1.4: Visualization (User Story 1 support)

#### Task 1.4.1: Implement Smith Chart Plotting

**User Story**: User Story 1 support (FR-015 - Smith charts)  
**Priority**: P1  
**Dependencies**: Task 1.2.1  
**Estimated Effort**: 4-5 hours

**TDD Steps**:
1. Write test: `test_plot_smith_chart_basic()` - verify plot renders
2. Write test: `test_smith_chart_before_after()` - original vs matched network
3. Implement: `plot_smith_chart()` wrapping scikit-rf (research.md Section 4)
4. Write test: `test_smith_chart_save_file()` - PNG output
5. Refactor: Styling (colors, markers, grid)

**Acceptance Criteria**:
- [X] Plots S11 on Smith chart using scikit-rf
- [X] Supports multiple networks on same chart (before/after comparison)
- [X] Saves to PNG, PDF, SVG formats
- [X] Customizable (labels, markers, colors)
- [X] All visualization tests pass

**Files**:
- `src/snp_tool/visualization/__init__.py`
- `src/snp_tool/visualization/smith_chart.py`
- `tests/unit/test_visualization.py`

---

#### Task 1.4.2: Implement Rectangular Plots (Return Loss, VSWR)

**User Story**: User Story 1 support (FR-015 - rectangular plots)  
**Priority**: P1  
**Dependencies**: Task 1.2.3  
**Estimated Effort**: 3-4 hours

**TDD Steps**:
1. Write test: `test_plot_return_loss()` - dB vs frequency
2. Write test: `test_plot_vswr()` - VSWR vs frequency with threshold line
3. Implement: Rectangular plotting functions
4. Write test: `test_plot_magnitude_phase()` - S-parameter mag/phase
5. Refactor: Consistent styling across plots

**Acceptance Criteria**:
- [X] Return loss plot (dB vs freq)
- [X] VSWR plot with threshold line (default 2.0)
- [X] Magnitude and phase plots
- [X] Saves to file formats (PNG, PDF, SVG)
- [X] All plot tests pass

**Files**:
- `src/snp_tool/visualization/rectangular.py`
- `src/snp_tool/visualization/metrics.py`
- `tests/unit/test_visualization.py` (extend)

---

#### Task 1.4.3: Implement CLI Plot Command

**User Story**: User Story 1 support (CLI visualization)  
**Priority**: P1  
**Dependencies**: Task 1.4.1, Task 1.4.2  
**Estimated Effort**: 2-3 hours

**TDD Steps**:
1. Write test: `test_cli_plot_smith()` - generate Smith chart
2. Write test: `test_cli_plot_vswr()` - generate VSWR plot
3. Implement: CLI plot command
4. Write test: `test_cli_plot_output_formats()` - PNG, PDF, SVG

**Acceptance Criteria**:
- [X] `snp-tool plot --type smith` generates Smith chart
- [X] `snp-tool plot --type vswr` generates VSWR plot
- [X] `--output` saves to file
- [X] `--show` displays interactive plot (if GUI available)
- [X] CLI plot tests pass

**Files**:
- `src/snp_tool/cli/commands.py` (extend with plot command)
- `tests/integration/test_cli_commands.py` (extend)

---

## P1 Integration & Acceptance Testing

### Task 1.INT.1: End-to-End CLI Workflow Tests

**User Story**: User Stories 1 & 2 complete workflow  
**Priority**: P1  
**Dependencies**: All Phase 1.1-1.4 tasks  
**Estimated Effort**: 4-6 hours

**TDD Steps**:
1. Write test: `test_full_workflow_load_add_export()` - complete user journey
2. Write test: `test_workflow_session_persistence()` - save/load (P3 preview)
3. Run: Integration tests against real SNP files
4. Verify: All acceptance scenarios from User Stories 1 & 2

**Acceptance Criteria**:
- [X] Load SNP → Display metrics → Add components → Verify updated metrics
- [X] All User Story 1 acceptance scenarios pass
- [X] All User Story 2 acceptance scenarios pass
- [X] Performance targets met (SC-001, SC-002)
- [X] CLI contract compliance verified

**Files**:
- `tests/integration/test_full_workflow.py`

---

## P2 Tasks: Enhancement (Should Have)

### Phase 2.1: Standard Component Library

#### Task 2.1.1: Implement E-Series Component Libraries

**User Story**: User Story 3 support (FR-016 - standard values mode)  
**Priority**: P2  
**Dependencies**: Task 1.1.2  
**Estimated Effort**: 3-4 hours

**TDD Steps**:
1. Write test: `test_get_standard_values_e12()` - verify E12 series
2. Write test: `test_get_standard_values_e24()` - verify E24 series
3. Implement: E-series generation (E12, E24, E96)
4. Write test: `test_snap_to_standard()` - 12.7pF → 12pF (E24)
5. Refactor: Decade range configuration

**Acceptance Criteria**:
- [X] E12, E24, E96 series values generated correctly
- [X] snap_to_standard() finds nearest value
- [X] Decade range configurable (pF to µF, pH to mH)
- [X] All component library tests pass

**Files**:
- `src/snp_tool/core/component_lib.py`
- `tests/unit/test_component_lib.py`

---

### Phase 2.2: Optimization Engine (User Story 3)

#### Task 2.2.1: Implement Objective Function

**User Story**: User Story 3 - Automated Optimization  
**Priority**: P2  
**Dependencies**: Task 1.3.2, Task 1.2.3, Task 2.1.1  
**Estimated Effort**: 8-10 hours

**TDD Steps**:
1. Write test: `test_objective_function_single_metric()` - return loss only
2. Write test: `test_objective_function_weighted()` - multiple metrics
3. Implement: Multi-metric weighted objective (research.md Section 1)
4. Write test: `test_objective_function_component_count_penalty()` - fewer components = lower cost
5. Write test: `test_objective_function_bandwidth_calculation()` - frequency range integration
6. Refactor: Normalize metrics to comparable scales

**Acceptance Criteria**:
- [X] Calculates weighted combination of return loss, VSWR, bandwidth, component count
- [X] Metrics normalized (0-1 scale for comparison)
- [X] Lower score = better solution (minimization)
- [X] All objective function tests pass

**Files**:
- `src/snp_tool/optimizer/__init__.py`
- `src/snp_tool/optimizer/objectives.py`
- `tests/unit/test_optimizer_objectives.py`

---

#### Task 2.2.2: Implement Optimization Engine

**User Story**: User Story 3 (FR-006, FR-017)  
**Priority**: P2  
**Dependencies**: Task 2.2.1  
**Estimated Effort**: 10-12 hours

**TDD Steps**:
1. Write test: `test_optimize_ideal_mode()` - continuous values
2. Write test: `test_optimize_standard_mode()` - E24 values only
3. Implement: `run_optimization()` with scipy.optimize.differential_evolution
4. Write test: `test_optimize_convergence()` - verify algorithm converges
5. Write test: `test_optimize_performance()` - <30 seconds for 2-component (SC-004)
6. Write test: `test_optimize_multiple_solutions()` - returns top 3, ranked by score
7. Refactor: Progress callback for CLI/GUI updates

**Acceptance Criteria**:
- [X] Ideal mode finds optimal continuous component values
- [X] Standard mode constrains to E12/E24/E96 series
- [X] Multiple solutions returned, ranked by score (FR-009)
- [ ] Performance: <30 seconds for 2-component matching (SC-004)
- [X] Progress callback works for UI updates
- [ ] All optimization engine tests pass

**Files**:
- `src/snp_tool/optimizer/engine.py`
- `src/snp_tool/optimizer/constraints.py`
- `tests/unit/test_optimizer_engine.py`
- `tests/performance/test_optimization_performance.py`

---

#### Task 2.2.3: Implement CLI Optimize Command

**User Story**: User Story 3 (CLI optimization)  
**Priority**: P2  
**Dependencies**: Task 2.2.2  
**Estimated Effort**: 6-8 hours

**TDD Steps**:
1. Write test: `test_cli_optimize_ideal()` - run optimization, verify solutions
2. Write test: `test_cli_optimize_standard_e24()` - E24 mode
3. Implement: CLI optimize command with progress bar
4. Write test: `test_cli_optimize_weights_parsing()` - parse weight string
5. Write test: `test_cli_apply_solution()` - apply chosen solution
6. Refactor: Interactive solution selection

**Acceptance Criteria**:
- [X] `snp-tool optimize` runs optimization with specified parameters
- [X] Progress bar updates during optimization
- [X] Displays top N solutions ranked by score
- [X] Interactive prompt to apply solution
- [X] `--json` output for automation
- [ ] All CLI optimize tests pass

**Files**:
- `src/snp_tool/cli/commands.py` (extend with optimize, apply-solution)
- `tests/integration/test_cli_optimization.py`

---

### Phase 2.3: GUI Implementation

#### Task 2.3.1: Implement GUI Main Window

**User Story**: User Stories 1-3 (GUI interface, FR-018)  
**Priority**: P2  
**Dependencies**: Task 1.3.4 (controller)  
**Estimated Effort**: 10-12 hours

**TDD Steps**:
1. Write test: `test_gui_main_window_init()` - window creates successfully
2. Write test: `test_gui_load_snp_file()` - file dialog, network loaded
3. Implement: PyQt6 main window with controller integration
4. Write test: `test_gui_smith_chart_widget()` - matplotlib canvas in Qt
5. Refactor: Layout with splitters (network info, plots, component panel)

**Acceptance Criteria**:
- [ ] Main window launches with menu bar (File, View, Help)
- [ ] File → Open SNP File loads network
- [ ] Smith chart and rectangular plots embedded in window
- [ ] Network information panel displays metrics
- [ ] All GUI tests pass (requires Qt test framework)

**Files**:
- `src/snp_tool/gui/mainwindow.py`
- `src/snp_tool/gui/widgets/__init__.py`
- `src/snp_tool/gui/widgets/smith_chart_widget.py`
- `tests/unit/test_gui_mainwindow.py` (PyQt6 tests)

---

#### Task 2.3.2: Implement GUI Component Panel

**User Story**: User Story 2 (GUI component addition)  
**Priority**: P2  
**Dependencies**: Task 2.3.1  
**Estimated Effort**: 6-8 hours

**TDD Steps**:
1. Write test: `test_gui_component_panel_add()` - add component via GUI
2. Write test: `test_gui_component_panel_validation()` - invalid value rejected
3. Implement: Component panel widget with form fields
4. Write test: `test_gui_component_list()` - displays added components
5. Write test: `test_gui_component_remove()` - remove component button
6. Refactor: Real-time plot updates on component changes

**Acceptance Criteria**:
- [ ] Component panel has port selector, type dropdown, value input, placement dropdown
- [ ] Engineering notation parsing in value field
- [ ] "Add Component" button adds to network
- [ ] Component list shows all added components
- [ ] Remove button deletes components
- [ ] Plots update in real-time (<1 second per FR-004)

**Files**:
- `src/snp_tool/gui/widgets/component_panel.py`
- `tests/unit/test_gui_component_panel.py`

---

#### Task 2.3.3: Implement GUI Optimization Panel

**User Story**: User Story 3 (GUI optimization)  
**Priority**: P2  
**Dependencies**: Task 2.3.1, Task 2.2.2  
**Estimated Effort**: 8-10 hours

**TDD Steps**:
1. Write test: `test_gui_optimizer_panel_init()` - panel creates with controls
2. Write test: `test_gui_run_optimization()` - button starts optimization in QThread
3. Implement: Optimization panel with settings (target impedance, weights, mode)
4. Write test: `test_gui_optimization_progress()` - progress bar updates
5. Write test: `test_gui_solutions_display()` - top solutions shown in list
6. Refactor: Non-blocking optimization (QThread)

**Acceptance Criteria**:
- [ ] Optimization panel has target impedance, frequency range, weights, mode controls
- [ ] "Run Optimization" button starts optimization in background thread
- [ ] Progress bar shows optimization progress
- [ ] Solutions list displays top results with metrics
- [ ] "Apply Solution" button applies selected solution
- [ ] GUI remains responsive during optimization

**Files**:
- `src/snp_tool/gui/widgets/optimizer_panel.py`
- `src/snp_tool/gui/dialogs/optimization_dialog.py`
- `tests/unit/test_gui_optimizer_panel.py`

---

#### Task 2.3.4: Integrate GUI with Controller

**User Story**: FR-019 (identical CLI/GUI results)  
**Priority**: P2  
**Dependencies**: Task 2.3.1, Task 2.3.2, Task 2.3.3  
**Estimated Effort**: 4-6 hours

**TDD Steps**:
1. Write test: `test_gui_uses_controller()` - GUI calls controller methods
2. Write test: `test_gui_cli_same_results()` - same network, same S-parameters
3. Implement: GUI → Controller signal/slot connections
4. Write test: `test_gui_workflow()` - end-to-end GUI workflow
5. Refactor: Ensure no business logic in GUI (only in controller)

**Acceptance Criteria**:
- [ ] GUI uses same controller as CLI
- [ ] All business logic in controller, not GUI widgets
- [ ] GUI and CLI produce identical S-parameter results
- [ ] FR-019 contract test passes

**Files**:
- `src/snp_tool/gui/mainwindow.py` (extend)
- `tests/integration/test_gui_cli_parity.py`

---

## P3 Tasks: Workflow Support (Nice to Have)

### Phase 3.1: Export Functionality (User Story 4)

#### Task 3.1.1: Implement SNP File Export

**User Story**: User Story 4 - Export Optimized Network  
**Priority**: P3  
**Dependencies**: Task 1.3.2  
**Estimated Effort**: 4-5 hours

**TDD Steps**:
1. Write test: `test_export_cascaded_snp()` - verify exported file format
2. Write test: `test_export_accuracy()` - 0.1 dB magnitude, 1 deg phase (SC-007)
3. Implement: SNP file export using scikit-rf
4. Write test: `test_export_loads_in_third_party_tools()` - compatibility
5. Refactor: Preserve original file metadata (frequency units, format)

**Acceptance Criteria**:
- [X] Exports cascaded S-parameters to new SNP file
- [X] Accuracy within 0.1 dB magnitude, 1 degree phase (SC-007)
- [X] Exported files load in third-party RF tools
- [X] Preserves frequency units and format type
- [X] All export tests pass

**Files**:
- `src/snp_tool/export/__init__.py`
- `src/snp_tool/export/snp_export.py`
- `tests/unit/test_export.py`

---

#### Task 3.1.2: Implement Component Configuration Export

**User Story**: User Story 4 (FR-010)  
**Priority**: P3  
**Dependencies**: Task 1.1.2  
**Estimated Effort**: 3-4 hours

**TDD Steps**:
1. Write test: `test_export_components_json()` - verify JSON schema
2. Write test: `test_export_components_yaml()` - YAML format
3. Implement: Component configuration export
4. Write test: `test_export_components_csv()` - CSV format for spreadsheets
5. Refactor: Include metadata (export date, source network, tool version)

**Acceptance Criteria**:
- [X] Exports component list to JSON (default)
- [X] Supports YAML and CSV formats
- [X] Includes all component details (port, type, value, placement, order)
- [X] Includes metadata (source network, export date)
- [X] All export tests pass

**Files**:
- `src/snp_tool/export/config_export.py`
- `tests/unit/test_export.py` (extend)

---

#### Task 3.1.3: Implement CLI Export Command

**User Story**: User Story 4 (CLI export)  
**Priority**: P3  
**Dependencies**: Task 3.1.1, Task 3.1.2  
**Estimated Effort**: 2-3 hours

**TDD Steps**:
1. Write test: `test_cli_export_snp()` - export SNP file
2. Write test: `test_cli_export_config()` - export component config
3. Implement: CLI export command
4. Write test: `test_cli_export_formats()` - JSON, YAML, CSV

**Acceptance Criteria**:
- [X] `snp-tool export --snp` exports cascaded S-parameters
- [X] `snp-tool export --config` exports component configuration
- [X] `--format` selects output format
- [ ] All CLI export tests pass

**Files**:
- `src/snp_tool/cli/commands.py` (extend with export)
- `tests/integration/test_cli_export.py`

---

### Phase 3.2: Session Persistence (User Story 5)

#### Task 3.2.1: Implement Session Save/Load

**User Story**: User Story 5 - Save and Resume Work Sessions  
**Priority**: P3  
**Dependencies**: Task 1.1.2, Task 3.1.2  
**Estimated Effort**: 6-8 hours

**TDD Steps**:
1. Write test: `test_save_session()` - verify JSON schema (research.md Section 5)
2. Write test: `test_load_session()` - restore complete state
3. Implement: Session save/load with JSON format
4. Write test: `test_session_roundtrip()` - save → load → identical state
5. Write test: `test_session_performance()` - <3 seconds (SC-012)
6. Write test: `test_session_version_migration()` - handle old versions
7. Refactor: SNP file checksum verification

**Acceptance Criteria**:
- [X] save_session() creates JSON file with all state
- [X] load_session() restores network, components, optimization results
- [X] Session file includes SNP file checksum for integrity
- [X] Version field enables future migration
- [X] Performance: <3 seconds for save/load (SC-012)
- [X] All session tests pass

**Files**:
- `src/snp_tool/utils/session_io.py`
- `tests/unit/test_session_io.py`
- `tests/integration/test_session_roundtrip.py`

---

#### Task 3.2.2: Implement CLI Session Commands

**User Story**: User Story 5 (CLI session persistence)  
**Priority**: P3  
**Dependencies**: Task 3.2.1  
**Estimated Effort**: 3-4 hours

**TDD Steps**:
1. Write test: `test_cli_save_session()` - save session file
2. Write test: `test_cli_load_session()` - restore session
3. Implement: CLI save-session and load-session commands
4. Write test: `test_cli_load_session_verify()` - checksum validation
5. Write test: `test_cli_load_session_missing_snp()` - error handling

**Acceptance Criteria**:
- [X] `snp-tool save-session` creates session file
- [X] `snp-tool load-session` restores session
- [X] `--verify` flag checks SNP file checksum
- [X] Error handling for missing SNP files, version incompatibility
- [ ] All CLI session tests pass

**Files**:
- `src/snp_tool/cli/commands.py` (extend with save-session, load-session)
- `tests/integration/test_cli_sessions.py`

---

#### Task 3.2.3: Implement GUI Session Menu

**User Story**: User Story 5 (GUI session persistence)  
**Priority**: P3  
**Dependencies**: Task 3.2.1, Task 2.3.1  
**Estimated Effort**: 4-5 hours

**TDD Steps**:
1. Write test: `test_gui_save_session_dialog()` - file save dialog
2. Write test: `test_gui_load_session_dialog()` - file open dialog
3. Implement: GUI File → Save Session, File → Load Session
4. Write test: `test_gui_session_restores_gui_state()` - window geometry, selected plot
5. Refactor: Recent sessions menu

**Acceptance Criteria**:
- [ ] File → Save Session opens save dialog
- [ ] File → Load Session opens file dialog and restores state
- [ ] GUI state (window geometry, selected plot) saved and restored
- [ ] Recent sessions menu (optional enhancement)
- [ ] All GUI session tests pass

**Files**:
- `src/snp_tool/gui/mainwindow.py` (extend with session menu actions)
- `src/snp_tool/gui/dialogs/session_dialogs.py`
- `tests/unit/test_gui_sessions.py`

---

## Cross-Cutting Tasks

### Task X.1: Documentation

**Priority**: All phases  
**Dependencies**: Ongoing  
**Estimated Effort**: Ongoing

**Deliverables**:
- [ ] README.md updated with installation, quickstart (from quickstart.md)
- [ ] API documentation (docstrings) in all modules
- [ ] CLI help text for all commands
- [ ] GUI tooltips for all controls
- [ ] Contributing guide (for open source)

**Files**:
- `README.md`
- `docs/` (if needed for detailed docs)

---

### Task X.2: Error Handling & Exception Hierarchy

**Priority**: All phases  
**Dependencies**: Task 1.1.1  
**Estimated Effort**: 3-4 hours

**TDD Steps**:
1. Write test: `test_exception_hierarchy()` - verify base class
2. Implement: Exception classes (contracts/core-api.md)
3. Write test: `test_validation_error_includes_report()` - ValidationError.report
4. Refactor: Use custom exceptions throughout codebase

**Acceptance Criteria**:
- [ ] SNPToolError base exception
- [ ] ValidationError, ComponentLimitError, OptimizationError, SessionError
- [ ] All exceptions include actionable messages
- [ ] Exception tests pass

**Files**:
- `src/snp_tool/exceptions.py`
- `tests/unit/test_exceptions.py`

---

### Task X.3: Continuous Integration (CI/CD)

**Priority**: P1 (after initial implementation)  
**Dependencies**: All unit tests  
**Estimated Effort**: 4-6 hours

**Deliverables**:
- [ ] GitHub Actions workflow (or equivalent CI)
- [ ] Run pytest on all pushes
- [ ] Run flake8, black, mypy linters
- [ ] Coverage report (target: 90%+)
- [ ] Automated deployment (PyPI package, optional)

**Files**:
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml` (optional)

---

## Task Summary

**Total Tasks**: 38

| Priority | Count | Estimated Hours |
|----------|-------|----------------|
| P1 (MVP) | 18 tasks | 112-142 hours |
| P2 (Enhancement) | 12 tasks | 82-104 hours |
| P3 (Workflow) | 8 tasks | 40-52 hours |
| **Total** | **38 tasks** | **234-298 hours** |

**Estimated Development Time**: 6-8 weeks (full-time developer)

---

## Implementation Order (Recommended)

**Week 1-2: Foundation (P1)**
1. Tasks 1.1.1 → 1.1.4 (Infrastructure)
2. Tasks 1.2.1 → 1.2.3 (SNP Parsing)
3. Task 1INT.1 (User Story 1 acceptance)

**Week 3-4: Component Addition (P1)**
4. Tasks 1.3.1 → 1.3.4 (Component Cascading)
5. Tasks 1.4.1 → 1.4.3 (Visualization)
6. Task 1.INT.1 (User Stories 1 & 2 acceptance)

**Week 5-6: Optimization (P2)**
7. Tasks 2.1.1 (Component Library)
8. Tasks 2.2.1 → 2.2.3 (Optimization Engine)

**Week 7-8: GUI & Polish (P2/P3)**
9. Tasks 2.3.1 → 2.3.4 (GUI Implementation)
10. Tasks 3.1.1 → 3.2.3 (Export & Sessions)

---

## Success Criteria Verification

After implementation, verify all success criteria from spec.md:

| Criteria | Verification Method | Target |
|----------|-------------------|--------|
| SC-001 | Performance test: load 10k freq points | <5 seconds |
| SC-002 | Performance test: add component to 1k points | <1 second |
| SC-003 | Integration test: optimization improvement | 10 dB in 90% cases |
| SC-004 | Performance test: optimization speed | <30 seconds |
| SC-005 | Integration test: full workflow | <5 minutes |
| SC-006 | Test with real analyzer files | 95% compatibility |
| SC-007 | Export accuracy test | 0.1 dB, 1 deg |
| SC-008 | User study (post-release) | 60% time reduction |
| SC-009 | User testing (GUI) | 80% first-time success |
| SC-010 | Stress test: 10k freq points | No degradation |
| SC-011 | CLI batch processing example | Works in scripts |
| SC-012 | Performance test: session I/O | <3 seconds |

---

## Ready for Implementation

**Status**: ✅ **Task decomposition complete**

All tasks follow TDD workflow per constitution:
1. Write failing test (Red)
2. Get user approval on test intent
3. Implement minimal code to pass (Green)
4. Refactor

**Next Step**: Begin implementation with **Task 1.1.1** (Project Setup)

**Branch**: `001-rf-impedance-optimizer`  
**Plan File**: `specs/001-rf-impedance-optimizer/plan.md`  
**Tasks File**: `specs/001-rf-impedance-optimizer/tasks.md` (this file)
