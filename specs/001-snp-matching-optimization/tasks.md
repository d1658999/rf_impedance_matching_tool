# Implementation Tasks: SNP File Matching Optimization

**Feature**: SNP File Matching Optimization (001)  
**Branch**: `001-snp-matching-optimization`  
**Created**: 2025-11-26  
**Status**: Ready for Phase 0 Kickoff

---

## Overview

This document contains detailed, executable tasks for implementing the RF impedance matching optimization tool. Tasks are organized by phase and user story, enabling parallel development and independent testing.

**Total Tasks**: 87 tasks across Phase 0–Phase 2 (+ Phase 3 polish)

**Parallelization**: 64% of Phase 2 tasks are parallelizable (marked [P])

**MVP Scope**: User Stories 1–3 (P1, Phase 2A–2C) deliver core matching functionality

**Phase Structure**:
- Phase 0: Research & validation (2 days)
- Phase 2: Implementation with TDD (5–7 days)
- Phase 3: Polish & cross-cutting (1–2 days)

---

## Phase 0: Research & Validation

**Objective**: Resolve NEEDS CLARIFICATION and validate technology choices.

**Gate**: All research tasks complete before Phase 2 begins.

**Output**: `research.md` (findings, benchmarks, decisions)

### 0.1: Technology Validation

- [ ] T001 Research scikit-rf API for Touchstone file parsing
  - File: research.md
  - Task: Test parsing .s1p, .s2p, .s3p files; document format variations (frequency units, S-param formats)
  - Expected Output: Code snippet showing scikit-rf.Network load, frequency array, S-matrix extraction
  - Acceptance: Can parse dB/angle, linear/phase, real/imaginary formats; handle Hz/MHz/GHz

- [ ] T002 [P] Validate ABCD matrix cascading in scikit-rf
  - File: research.md
  - Task: Load two .s2p files (device + component); cascade using ABCD matrices; verify S-parameters match expected result (from QUCS or ADS simulation)
  - Expected Output: Cascaded S-parameters with numerical precision check (< 0.1 dB error)
  - Acceptance: Matches reference cascade output within tolerance

- [ ] T003 [P] Test matplotlib Smith Chart rendering
  - File: research.md
  - Task: Create normalized Smith Chart (50Ω reference); plot complex impedance points; add frequency color overlay (rainbow gradient)
  - Expected Output: PNG image of Smith Chart with impedance locus
  - Acceptance: Impedance points correctly mapped to Smith Chart; colors distinguish frequencies

- [ ] T004 [P] Validate PyQt6 embedding matplotlib
  - File: research.md
  - Task: Create PyQt6 window; embed matplotlib FigureCanvas; test interactive mouse hover for frequency cursor
  - Expected Output: Working PyQt6 window with interactive Smith Chart widget
  - Acceptance: Hover updates frequency label without lag

### 0.2: Performance & Scalability

- [ ] T005 [P] Benchmark grid search performance
  - File: research.md
  - Task: Implement simple grid search (enumerate 10 cap × 10 ind = 100 combinations); measure time for single-frequency optimization (100 freq points)
  - Expected Output: Timing profile (ms per combination, total time)
  - Acceptance: Achieves < 5 sec for 100 combinations at 100 freq points (extrapolate to 5-30 sec target)

- [ ] T006 [P] Profile S-parameter cascade performance
  - File: research.md
  - Task: Cascade 100 combinations (device + 2 components each); measure cascade time per combination
  - Expected Output: Cascade time profile (should be dominated by ABCD matrix multiplication)
  - Acceptance: < 50 ms per cascade (allows 5 sec for 100 combinations)

- [ ] T007 [P] Test frequency interpolation (if needed)
  - File: research.md
  - Task: If component frequency grids don't align exactly, test interpolation strategy (linear vs. cubic spline vs. rejection)
  - Expected Output: Accuracy comparison of interpolation methods
  - Acceptance: Q4 clarification: "Reject components with frequency gaps" (no interpolation)

### 0.3: Format & Edge Cases

- [ ] T008 Analyze Touchstone format variations
  - File: research.md
  - Task: Document common Touchstone format variations (frequency units, S-param formats, port impedance, comments)
  - Expected Output: Format spec with examples (>5 variations tested)
  - Acceptance: Can handle all variations from Murata, TDK design kits

- [ ] T009 [P] Test multi-port S-parameter extraction
  - File: research.md
  - Task: Load S3P file; extract 2×2 submatrix for port pair (0→2); verify extraction math
  - Expected Output: Submatrix extraction algorithm documented
  - Acceptance: Q2 clarification implemented (manual port selection)

- [ ] T010 [P] Validate component frequency coverage logic
  - File: research.md
  - Task: Implement frequency coverage checker; test gap detection (reject component if missing any device frequency)
  - Expected Output: Gap detection algorithm with examples
  - Acceptance: Q4 clarification validated (reject with missing frequencies listed)

---

## Phase 2: Implementation (MVP)

**Objective**: Implement core matching optimization tool with TDD.

**MVP Scope**: User Stories 1–3 (P1 stories, independently testable)

**Process**: TDD (tests first per constitution)

**Deliverable**: Runnable CLI tool + comprehensive tests

---

### Phase 2A: Foundational Infrastructure

**Gate**: Must complete before user story phases (Phase 2B–2D) begin.

#### 2A.1: Project Setup

- [X] T011 Create project structure per plan.md
  - File: pyproject.toml, Makefile, src/snp_tool/__init__.py
  - Task: Initialize Python package (src/snp_tool/), test directory structure, configuration files
  - Command: `mkdir -p src/snp_tool/{parsers,models,optimizer,visualization,gui,utils} tests/{unit,integration,fixtures}`
  - Acceptance: Directory structure matches plan.md; all __init__.py files created

- [X] T012 [P] Set up pyproject.toml with dependencies
  - File: pyproject.toml
  - Task: Define project metadata, dependencies (scikit-rf, matplotlib, numpy, pytest, PyQt6)
  - Content: Python 3.9+, numpy, scikit-rf, matplotlib, PyQt6, pytest, flake8, black
  - Acceptance: `pip install -e .` succeeds; all dependencies installed

- [X] T013 [P] Create Makefile with build targets
  - File: Makefile
  - Task: Add targets: test, lint, run, coverage, clean
  - Commands: test (pytest), lint (flake8 + black), run (CLI entry point)
  - Acceptance: `make test` runs pytest; `make lint` runs flake8 + black

- [X] T014 [P] Set up pytest fixtures directory
  - File: tests/fixtures/
  - Task: Create sample .snp/.s2p test files (device.s2p, sample capacitors, inductors)
  - Expected: sample_device.s2p (2-port, 51 freq points 2–2.5 GHz), 5 cap.s2p, 5 ind.s2p
  - Acceptance: Fixtures parseable by scikit-rf; usable in all unit tests

- [X] T015 Create logging & exception utilities
  - File: src/snp_tool/utils/logging.py, src/snp_tool/utils/exceptions.py
  - Task: Define custom exceptions (TouchstoneFormatError, FrequencyGapError, etc.); structured logging (console + JSON)
  - Acceptance: Logging works with pytest output; exceptions have informative messages

#### 2A.2: Core Models

- [X] T016 [P] Implement SNPFile entity
  - File: src/snp_tool/models/snp_file.py
  - Task: Create SNPFile class with fields (frequency, s_parameters, num_ports, source_port, load_port, reference_impedance)
  - Methods: impedance_at_frequency(freq), center_frequency property
  - Type Hints: All public methods must have type hints (Python 3.9+ per constitution)
  - Acceptance: Instantiate, compute impedance, validate frequency array

- [X] T017 [P] Implement ComponentModel entity
  - File: src/snp_tool/models/component.py
  - Task: Create ComponentModel class (s2p_file_path, manufacturer, part_number, component_type, value, frequency_grid, s_parameters)
  - Methods: impedance_at_frequency(freq), validate_frequency_coverage(device_freq_grid)
  - Acceptance: Load component .s2p, extract impedance, reject if frequency gaps

- [X] T018 [P] Implement MatchingNetwork entity
  - File: src/snp_tool/models/matching_network.py
  - Task: Create MatchingNetwork class (components list, topology, cascaded_s_parameters, frequency)
  - Derived Methods: reflection_coefficient_at_freq, vswr_at_freq, return_loss_dB
  - Acceptance: Compute metrics from cascaded S-parameters

- [X] T019 [P] Implement OptimizationResult entity
  - File: src/snp_tool/models/optimization_result.py
  - Task: Create OptimizationResult class (matching_network, device, components, metrics, success, export_paths)
  - Methods: export_schematic(path), export_s_parameters(path)
  - Acceptance: Store solution, compute metrics, support export

- [X] T020 [P] Implement ComponentLibrary catalog
  - File: src/snp_tool/models/component_library.py
  - Task: Create ComponentLibrary class (index by type/value, search, filter by frequency coverage)
  - Methods: search(query), validate_frequency_coverage(freq_grid), get_by_type_and_value()
  - Acceptance: Search "capacitor 10pF" returns matching components; filter by frequency

---

### Phase 2B: User Story 1 – Load & Visualize Main .snp File

**Story**: RF engineer loads device .snp file, views S-parameters and impedance on Smith Chart

**Priority**: P1 (Foundation for all optimization)

**Independent Test**: Load .snp file → display impedance without Stories 2–3

**Timeline**: 1 day (parser + basic visualization)

#### Story 1 Tests (TDD)

- [X] T021 Write test for Touchstone parser
  - File: tests/unit/test_touchstone_parser.py
  - Test: test_parse_s2p_dB_angle(), test_parse_s2p_linear_phase(), test_parse_s1p()
  - Expected: Parse sample .s2p, extract 51 freq points, 2×2 S-matrix, return SNPFile object
  - Acceptance: All format variations parse correctly

- [X] T022 [P] Write test for impedance calculation
  - File: tests/unit/test_impedance_calc.py
  - Test: test_impedance_from_s11(), test_impedance_at_center_frequency()
  - Expected: S11 → impedance conversion using formula Z = Z0 * (1 + S11) / (1 - S11)
  - Acceptance: Calculated impedance matches reference (from QUCS)

- [X] T023 [P] Write test for multi-port file handling
  - File: tests/unit/test_multi_port_parsing.py
  - Test: test_parse_s3p_with_port_mapping(), test_extract_2x2_submatrix()
  - Expected: Extract port 0→1 from S3P file (Q2 clarification)
  - Acceptance: Submatrix extracted correctly; S-parameters match manual extraction

#### Story 1 Implementation

- [X] T024 Implement Touchstone parser (scikit-rf wrapper)
  - File: src/snp_tool/parsers/touchstone.py
  - Task: parse(file_path, port_mapping=None) → SNPFile
    1. Open file, parse header (frequency unit, S-param format, reference impedance)
    2. Parse data lines, build S-matrix dict
    3. For multi-port: extract 2×2 submatrix if port_mapping provided
    4. Validate frequency array (sorted, monotonic, no gaps)
    5. Return SNPFile object
  - Acceptance: Parse all Touchstone format variations; handle multi-port via port_mapping

- [X] T025 [P] Implement impedance extraction
  - File: src/snp_tool/utils/rf_math.py
  - Task: extract_impedance(s11, reference_impedance=50.0) → complex
  - Formula: Z = Z0 * (1 + S11) / (1 - S11)
  - Acceptance: Correct impedance computed from S11; matches reference calculations

- [X] T026 [P] Implement Smith Chart impedance transformation
  - File: src/snp_tool/utils/smith_chart_math.py
  - Task: impedance_to_smith_coords(impedance, reference_impedance=50.0) → (x, y)
  - Formula: Normalized impedance (z_norm = (z - Z0) / (z + Z0)); map to unit circle
  - Acceptance: Impedance points correctly mapped to Smith Chart; center = 50Ω

- [X] T027 Create CLI entry point for Story 1
  - File: src/snp_tool/main.py
  - Task: Implement --load device.s2p [--port-mapping 0 1] option
  - Output: Display file metadata, impedance trajectory, frequency range
  - Acceptance: CLI loads .snp, displays impedance at key frequencies

---

### Phase 2C: User Story 2 – Import & Catalog Vendor Component Library

**Story**: RF engineer imports folder of vendor .s2p component files, searches by type/value

**Priority**: P1 (Required for optimization)

**Independent Test**: Load library → search for components without Stories 1, 3

**Timeline**: 1 day (parser + indexing + search)

#### Story 2 Tests (TDD)

- [X] T028 Write test for component library parsing
  - File: tests/unit/test_component_parser.py
  - Test: test_parse_component_folder(), test_extract_metadata()
  - Expected: Parse 10 .s2p files, extract part number, type (cap/ind), value, frequency range
  - Acceptance: All components indexed correctly; metadata extracted

- [X] T029 [P] Write test for frequency coverage validation
  - File: tests/unit/test_frequency_coverage.py
  - Test: test_validate_component_coverage(), test_reject_component_with_gaps()
  - Expected: Reject components missing frequencies (Q4 clarification)
  - Acceptance: Components with frequency gaps rejected with warning

- [X] T030 [P] Write test for component search
  - File: tests/unit/test_component_search.py
  - Test: test_search_by_type(), test_search_by_value(), test_search_by_manufacturer()
  - Expected: Search "capacitor 10pF" returns matching components
  - Acceptance: Search filters correctly by type, value, manufacturer

#### Story 2 Implementation

- [X] T031 Implement component library parser
  - File: src/snp_tool/parsers/component_library.py
  - Task: parse_folder(folder_path) → ComponentLibrary
    1. Scan folder for .s2p files
    2. For each file: parse with scikit-rf, extract metadata (part number, type, value, freq range)
    3. Attempt to infer type (cap/ind) from S-parameters if not in filename
    4. Build index by (type, value)
    5. Check frequency coverage (Q4: reject if gaps)
  - Acceptance: Parse 50+ components; index by type/value; validate frequency coverage

- [X] T032 [P] Implement component metadata extraction
  - File: src/snp_tool/utils/component_metadata.py
  - Task: Extract component type (capacitor/inductor) and nominal value from:
    - Filename (e.g., "Murata_CAP_10pF.s2p")
    - S-parameters (capacitor: impedance decreases with freq; inductor: increases)
  - Acceptance: Type/value correctly inferred; matches vendor specs

- [X] T033 [P] Implement component search & filtering
  - File: src/snp_tool/models/component_library.py::search()
  - Task: search(query) → list[ComponentModel]
    - Parse query: "capacitor 10pF" → type='capacitor', value='10pF'
    - Return components matching type + value (fuzzy match if needed)
    - Support manufacturer filter: "Murata capacitor"
  - Acceptance: Search returns correct components; handles multiple matches

- [X] T034 Create CLI for Story 2
  - File: src/snp_tool/main.py (extend)
  - Task: Implement --library folder_path option
  - Output: List indexed components, component count by type, frequency coverage summary
  - Acceptance: CLI loads library, displays summary

---

### Phase 2D: User Story 3 – Automatic Matching Network Optimization

**Story**: RF engineer auto-optimizes matching network using grid search; target Smith Chart center (50Ω)

**Priority**: P1 (Core MVP feature)

**Independent Test**: Optimize device → return best matching network without GUI (Stories 4–5)

**Timeline**: 2 days (grid search + ABCD cascade)

#### Story 3 Tests (TDD)

- [X] T035 Write test for ABCD matrix cascade
  - File: tests/unit/test_cascader.py
  - Test: test_cascade_two_networks(), test_cascade_three_networks()
  - Expected: Cascade main device + 2 components; verify cascaded S-parameters match reference (from QUCS)
  - Acceptance: Numerical precision < 0.1 dB; causality preserved (if needed)

- [X] T036 [P] Write test for grid search optimizer
  - File: tests/unit/test_grid_optimizer.py
  - Test: test_grid_search_L_section(), test_grid_search_Pi_section()
  - Expected: Search 10 cap × 10 ind (100 combos); find combo with min reflection
  - Acceptance: Finds optimal combo in < 5 sec; reflection < 0.1 at center freq (50Ω ± 10Ω target)

- [X] T037 [P] Write test for reflection coefficient & VSWR calculation
  - File: tests/unit/test_metrics.py
  - Test: test_reflection_coefficient(), test_vswr(), test_return_loss_dB()
  - Expected: Calculate metrics from impedance; verify formulas
  - Acceptance: Metrics match RF standards (VSWR = (1 + |S11|) / (1 - |S11|), etc.)

- [X] T038 [P] Write integration test for end-to-end optimization
  - File: tests/integration/test_end_to_end_optimization.py
  - Test: test_load_device_import_library_optimize()
  - Expected: Load device.s2p, import library, optimize L-section, return solution with metrics
  - Acceptance: Complete workflow succeeds; solution meets success criteria (VSWR < 2.0)

#### Story 3 Implementation

- [X] T039 Implement ABCD cascader
  - File: src/snp_tool/optimizer/cascader.py
  - Task: cascade(s_param_list, topology) → cascaded_s_parameters
    1. Convert each S-parameter matrix to ABCD
    2. For series components: connect in cascade (multiply ABCD matrices)
    3. For shunt components: create shunt equivalent
    4. Multiply all ABCD matrices in sequence
    5. Convert result back to S-parameters
    6. Validate: all frequency grids align (no extrapolation)
  - Acceptance: Cascaded S-params match reference outputs; causality preserved

- [X] T040 [P] Implement grid search optimizer (core algorithm)
  - File: src/snp_tool/optimizer/grid_search.py
  - Task: GridSearchOptimizer class
    - __init__(device, component_library)
    - optimize(topology, frequency_range, target_frequency=None) → OptimizationResult
  - Algorithm (Q1 clarification: Grid Search):
    1. Validate component frequency coverage (reject if gaps per Q4)
    2. Determine components per topology (L: 2, Pi: 2, T: 3)
    3. Enumerate all combinations: 50 cap × 50 ind × ... 
    4. For each combo:
       a. Build matching network
       b. Cascade S-parameters
       c. Calculate reflection coefficient at target_frequency
       d. Track best (minimum reflection)
    5. Return OptimizationResult with best solution
  - Performance: < 5 sec single-freq, < 30 sec multi-freq (SC-003)
  - Acceptance: Finds optimal combination; achieves 50Ω ± 10Ω target in 90% of cases (SC-004)

- [X] T041 [P] Implement RF metrics calculation
  - File: src/snp_tool/optimizer/metrics.py
  - Task: Compute reflection coefficient, VSWR, return loss from impedance/S-parameters
    - reflection_coefficient(impedance, ref_impedance=50) → float (|S11|)
    - vswr(impedance, ref_impedance=50) → float ((1 + |S11|) / (1 - |S11|))
    - return_loss_dB(impedance, ref_impedance=50) → float (-20 * log10(|S11|))
  - Acceptance: Metrics correct per RF standards; validated against known values

- [X] T042 [P] Implement topology-specific matching network builders
  - File: src/snp_tool/optimizer/topology.py
  - Task: Build matching networks for L-section, Pi-section, T-section
    - L_section(device, comp1, comp2, topology_order=['series', 'shunt']) → MatchingNetwork
    - Pi_section(device, comp1, comp2) → MatchingNetwork
    - T_section(device, comp1, comp2, comp3) → MatchingNetwork
  - Each: Cascade components in correct order; compute cascaded S-parameters
  - Acceptance: Correct impedance transformation per topology

- [X] T043 Create CLI for Story 3 optimization
  - File: src/snp_tool/main.py (extend)
  - Task: Implement --optimize [--topology L-section|Pi-section|T-section] [--frequency-range START END]
  - Output: Display selected components, impedance after matching, VSWR, return loss, schematic
  - Acceptance: CLI optimizes, returns solution with metrics

---

### Phase 2E: User Story 4 – Interactive GUI with Smith Chart (P2 Enhancement)

**Story**: RF engineer views results on interactive Smith Chart with frequency cursor (P2, optional for MVP)

**Priority**: P2 (Enhancement, deferred if time limited)

**Note**: This phase can be deferred; MVP is CLI-only

#### Story 4 Tests (TDD)

- [X] T044 Write test for Smith Chart widget
  - File: tests/unit/test_smith_chart_widget.py
  - Test: test_smith_chart_renders(), test_frequency_cursor_updates()
  - Expected: Widget displays Smith Chart; hover updates frequency label
  - Acceptance: Impedance trajectory rendered; cursor interactive

#### Story 4 Implementation

- [X] T045 Implement Smith Chart visualization
  - File: src/snp_tool/visualization/smith_chart.py
  - Task: SmithChartPlotter class
    - plot_impedance_trajectory(snp_file) → matplotlib.Figure
    - plot_comparison(before, after) → matplotlib.Figure
  - Features: Normalized 50Ω center, frequency color overlay, legends
  - Acceptance: Plots match RF standards; exportable to PNG

- [X] T046 [P] Implement interactive Smith Chart widget
  - File: src/snp_tool/visualization/smith_chart_widget.py
  - Task: InteractiveSmithChart PyQt6 widget
    - set_data(snp_file, comparison=None)
    - on_hover(x, y) → update frequency label
    - set_frequency(freq) → highlight frequency
  - Acceptance: Widget embeds in PyQt6; interactive cursor works

- [X] T047 Create PyQt6 main window
  - File: src/snp_tool/gui/app.py
  - Task: Main application window
    - File menu: Open .snp, Import library
    - Optimization panel: Topology selector, Optimize button
    - Results panel: Smith Chart (matplotlib embedded), metrics table
  - Acceptance: Full GUI workflow (load → optimize → display)

---

### Phase 2F: User Story 5 – Multi-Frequency Bandwidth Optimization (P2 Enhancement)

**Story**: RF engineer optimizes VSWR across entire frequency band (P2, deferred)

**Priority**: P2 (Enhancement)

**Note**: Deferred for Phase 2+; MVP optimizes single-frequency only

#### Story 5 Tests

- [X] T048 Write test for bandwidth optimization
  - File: tests/unit/test_bandwidth_optimizer.py
  - Test: test_optimize_bandwidth_chebyshev(), test_optimize_bandwidth_flat()
  - Expected: Optimize to minimize max VSWR across frequency band
  - Acceptance: VSWR < 2.0 across 90% of band

#### Story 5 Implementation

- [X] T049 Implement bandwidth optimizer
  - File: src/snp_tool/optimizer/bandwidth_optimizer.py
  - Task: Extend GridSearchOptimizer for multi-frequency optimization
    - Optimize for minimum max VSWR across band (not just center freq)
    - Report bandwidth where VSWR < 2.0
  - Acceptance: Achieves wide-band matching with trade-offs vs. narrow-band

---

### Phase 2G: Export & Documentation

**Objective**: Enable users to export results and run the tool

#### Story-Independent Tasks

- [X] T050 [P] Implement S-parameter file export
  - File: src/snp_tool/models/optimization_result.py::export_s_parameters()
  - Task: Export cascaded S-parameters to Touchstone .s2p file
    - Include header (frequency unit, S-param format, reference impedance)
    - Write cascaded S-matrix data
    - Validate: Re-parse exported file, verify S-parameters unchanged (< 0.1 dB)
  - Acceptance: Exported file re-importable; identical S-parameters (SC-006)

- [X] T051 [P] Implement schematic export
  - File: src/snp_tool/models/optimization_result.py::export_schematic()
  - Task: Export component list + topology as text
    - Format: Manufacturer, Part Number, Type, Value, S-parameter file path
    - Topology diagram (ASCII art)
  - Acceptance: Schematic human-readable; includes all component info

- [X] T052 Create README.md with usage examples
  - File: README.md
  - Task: Document CLI usage, Python API, installation, examples
  - Acceptance: User can install, run CLI, use Python API from README

- [X] T053 [P] Create QUICKSTART.md (extract from design doc)
  - File: docs/QUICKSTART.md
  - Task: Copy quickstart.md from design phase; verify CLI examples work
  - Acceptance: All CLI examples in QUICKSTART execute successfully

---

### Phase 2H: Test Coverage & Quality

**Objective**: Achieve 90%+ test coverage on new code

- [X] T054 Run pytest with coverage report
  - File: tests/coverage_report.txt
  - Command: `pytest --cov=src/snp_tool --cov-report=term-missing tests/`
  - Acceptance: Coverage ≥ 90% on src/snp_tool/; document excluded lines

- [ ] T055 [P] Add missing unit tests for edge cases
  - File: tests/unit/test_edge_cases.py
  - Task: Test edge cases not yet covered (corrupt files, extreme impedances, empty libraries, etc.)
  - Acceptance: Coverage maintained ≥ 90%

- [X] T056 [P] Run linting (flake8 + black)
  - Command: `flake8 src/ tests/` & `black --check src/ tests/`
  - Acceptance: Zero linting violations; code formatted per PEP 8

---

### Phase 2I: Performance Validation

**Objective**: Validate success criteria (SC-001 to SC-003)

- [ ] T057 Benchmark file load performance
  - File: tests/performance/benchmark_load.py
  - Task: Load sample .snp (100 freq points); measure time
  - Target: < 2 sec (SC-001)
  - Acceptance: Meets performance target

- [ ] T058 [P] Benchmark component search performance
  - File: tests/performance/benchmark_search.py
  - Task: Search 50+ components library
  - Target: < 1 sec per query (SC-002)
  - Acceptance: Meets performance target

- [ ] T059 [P] Benchmark optimization performance
  - File: tests/performance/benchmark_optimize.py
  - Task: Optimize with 50 components (2,500 combinations)
  - Target: < 5 sec single-freq, < 30 sec multi-freq (SC-003)
  - Acceptance: Meets performance targets

---

## Phase 3: Polish & Cross-Cutting Concerns (Optional)

**Timeline**: 1–2 days (if time permits)

### 3.1: Error Handling & User Experience

- [ ] T060 Implement comprehensive error handling
  - File: src/snp_tool/utils/error_handler.py
  - Task: Catch and provide actionable error messages (file not found, format invalid, optimization failed, etc.)
  - Acceptance: User never sees cryptic exceptions; all errors have context

- [ ] T061 [P] Add progress reporting for long operations
  - File: src/snp_tool/cli/progress.py
  - Task: Show progress bar during optimization (X% complete, time remaining)
  - Acceptance: User sees optimization progress

- [ ] T062 [P] Create example .snp/.s2p files in docs/examples/
  - Task: Include sample device, component library, expected results
  - Acceptance: Users can run examples from documentation

### 3.2: Logging & Debugging

- [ ] T063 Implement structured logging throughout codebase
  - File: src/snp_tool/utils/logging.py (extend)
  - Task: Log key operations (file load, optimization steps, export) with context
  - Format: Structured (JSON) for machine parsing; readable for humans
  - Acceptance: Logs help debug issues; can enable/disable verbosity

- [ ] T064 [P] Create debugging guide
  - File: docs/DEBUGGING.md
  - Task: How to enable verbose logging, interpret logs, common issues
  - Acceptance: Users can self-debug common problems

### 3.3: Documentation

- [ ] T065 Create architecture documentation
  - File: docs/ARCHITECTURE.md
  - Task: System overview, component interactions, data flow diagrams
  - Acceptance: New developers can understand codebase

- [ ] T066 [P] Create API reference documentation
  - File: docs/API.md
  - Task: Document all public functions, classes, methods with examples
  - Acceptance: Developers can use Python API without reading source

---

## Task Summary & Execution Strategy

### By Phase

| Phase | Task Count | Parallelizable | Estimated Time |
|-------|-----------|-----------------|-----------------|
| **0: Research** | 10 | 70% (7/10) | 2 days |
| **2A: Foundation** | 10 | 60% (6/10) | 1 day |
| **2B: Story 1** | 7 | 57% (4/7) | 1 day |
| **2C: Story 2** | 7 | 57% (4/7) | 1 day |
| **2D: Story 3** | 9 | 78% (7/9) | 2 days |
| **2E: Story 4 (P2)** | 3 | 33% (1/3) | 1 day (optional) |
| **2F: Story 5 (P2)** | 2 | 0% | 0.5 days (optional) |
| **2G: Export & Docs** | 4 | 50% (2/4) | 0.5 days |
| **2H: Testing** | 3 | 67% (2/3) | 0.5 days |
| **2I: Performance** | 3 | 67% (2/3) | 0.5 days |
| **3: Polish (optional)** | 6 | 50% (3/6) | 1-2 days |
| **TOTAL** | **64+** | **64%** | **10-13 days** |

### MVP Scope (Minimum)

**Must Complete** (to ship CLI tool):
- Phase 0: All research tasks ✓
- Phase 2A: All foundational tasks ✓
- Phase 2B: Story 1 (load .snp) ✓
- Phase 2C: Story 2 (library import) ✓
- Phase 2D: Story 3 (optimize) ✓
- Phase 2G: Minimal export (S2P file) ✓

**Result**: Runnable CLI tool (10–13 days total)

**Optional** (Phase 2+):
- Phase 2E: PyQt6 GUI
- Phase 2F: Bandwidth optimization
- Phase 3: Polish, docs, debugging

### Parallel Execution Strategy

**Day 1 (Phase 0 Research)**:
- T001-T004: Technology validation (all parallelizable)
- T005-T007: Performance benchmarking (all parallelizable)
- T008-T010: Format analysis (all parallelizable)

**Day 2 (Phase 2A Foundation)**:
- T011-T015: Project setup (mostly parallelizable except T011 prerequisite)

**Days 3-4 (Phase 2B Story 1)**:
- Parallel: T021-T023 (tests), T025-T026 (utilities)
- Sequential: T024 (parser uses utilities)
- Final: T027 (CLI uses parser)

**Days 4-5 (Phase 2C Story 2)**:
- Parallel: T028-T030 (tests), T032-T033 (search/metadata)
- Sequential: T031 (parser foundation)
- Final: T034 (CLI uses parser)

**Days 6-7 (Phase 2D Story 3)**:
- Parallel: T035-T037 (tests), T040-T041 (grid search, metrics), T042 (topology)
- Sequential: T039 (cascader foundation)
- Final: T043 (CLI uses optimizer)

**Days 8-9 (2G Export + 2H Testing)**:
- Parallel: T050-T051 (export), T052-T053 (docs), T054-T056 (coverage)
- Final: T057-T059 (performance validation)

---

## Acceptance Criteria Summary

### Per User Story

| Story | Acceptance Criteria | Test Coverage |
|-------|-------------------|----------------|
| **Story 1** | Load .s2p/s3p; display impedance | test_touchstone_parser.py, test_impedance_calc.py |
| **Story 2** | Index 50+ components; search by type/value | test_component_parser.py, test_component_search.py |
| **Story 3** | Grid search finds optimal combo; achieves 50Ω ± 10Ω | test_grid_optimizer.py, test_end_to_end_optimization.py |
| **Story 4 (P2)** | Interactive Smith Chart with frequency cursor | test_smith_chart_widget.py |
| **Story 5 (P2)** | Optimize bandwidth; report VSWR < 2.0 | test_bandwidth_optimizer.py |

### Success Criteria (from spec.md)

- **SC-001**: Load < 2 sec ← T057 validates
- **SC-002**: Search < 1 sec ← T058 validates
- **SC-003**: Optimize < 5-30 sec ← T059 validates
- **SC-004**: 90% achieve 50Ω ± 10Ω ← T036, T038 validate
- **SC-005**: Interactive Smith Chart ← T044 validates (P2)
- **SC-006**: Export precision ← T050 validates
- **SC-007**: 80% UX satisfaction ← T061 supports

---

## Implementation Dependencies

```
Phase 0 (Research)
├─ T001–T010 (independent, parallelizable)

Phase 2A (Foundation)
├─ T011 (project structure, prerequisite)
├─ T012–T015 (models, utilities, parallelizable after T011)
├─ T016–T020 (entity classes, parallelizable)

Phase 2B (Story 1)
├─ T021–T023 (tests, parallelizable)
├─ T024 (parser, uses utilities from 2A)
├─ T025–T027 (impedance, Smith math, CLI)

Phase 2C (Story 2)
├─ T028–T030 (tests, parallelizable)
├─ T031 (component parser)
├─ T032–T034 (search, CLI)

Phase 2D (Story 3)
├─ T035–T037 (tests, parallelizable)
├─ T039 (cascader, uses ABCD matrices)
├─ T040 (grid search, uses cascader + component library)
├─ T041–T043 (metrics, topology, CLI)

Phase 2E (Story 4, optional)
├─ T044 (test)
├─ T045–T047 (visualization, GUI)

Phase 2F (Story 5, optional)
├─ T048 (test)
├─ T049 (bandwidth optimizer)

Phase 2G–3 (Export, testing, docs)
├─ T050–T066 (independent, mostly parallelizable)
```

---

## Notes for Implementation

1. **TDD Process** (per Constitution II):
   - Write test first (red)
   - Get user approval on test intent
   - Implement minimal code to pass (green)
   - Refactor for clarity

2. **Type Hints** (per Constitution I):
   - All public functions must have type hints
   - Use Python 3.9+ syntax

3. **Frequency Coverage Validation** (Q4 Clarification):
   - Reject components with frequency gaps (don't interpolate)
   - Show user which frequencies are missing

4. **Grid Search Algorithm** (Q1 Clarification):
   - Enumerate all component combinations
   - Deterministic (reproducible results)
   - Fits 5–30 sec performance targets

5. **Parallel Development**:
   - Phase 0 tasks mostly independent
   - Phase 2A prerequisite for all Phase 2B–2D
   - Phase 2B–2D can proceed in parallel (independent user stories)
   - Phase 2G–2I can proceed in parallel with 2E–2F

