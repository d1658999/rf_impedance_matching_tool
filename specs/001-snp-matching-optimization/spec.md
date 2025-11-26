# Feature Specification: SNP File Matching Optimization

**Feature Branch**: `001-snp-matching-optimization`  
**Created**: 2025-11-26  
**Status**: Draft  
**Input**: RF engineer workflow for impedance matching using vendor design kits and automatic optimization targeting Smith Chart center

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load and Visualize Main Simulation File (Priority: P1)

**Why this priority**: RF engineers must load their primary device .snp file before any optimization can begin. This is the foundational input that drives all subsequent analysis.

**Independent Test**: Can import a .snp file (single or multiple ports) and display its S-parameters in a user-readable format (table or chart view) without requiring any subsequent optimization.

**Acceptance Scenarios**:

1. **Given** RF engineer has a main device .snp file (S1P, S2P, S3P, etc.), **When** user selects "Load Main File" and chooses the file, **Then** system displays file metadata (frequency range, port count), loads S-parameters, and shows confirmation message.
2. **Given** file is successfully loaded, **When** user selects a frequency point, **Then** system displays impedance at that frequency in both rectangular (R+jX) and polar (|Z|∠φ) formats.
3. **Given** main file loaded, **When** user scrolls or selects frequency range, **Then** system displays S11 (or equivalent reflection) on Smith Chart overlay, centered for visibility.

---

### User Story 2 - Import and Catalog Vendor Component Library (Priority: P1)

**Why this priority**: Access to multiple vendor design kits (Murata, TDK S2P files) is essential for engineers to compose matching networks. Without a curated library, engineers must manually manage dozens of files.

**Independent Test**: Can import a folder of vendor .s2p files (capacitor/inductor models), catalog them by component type and value, and display searchable list with key parameters (frequency range, S-parameters at center frequency).

**Acceptance Scenarios**:

1. **Given** RF engineer has a folder of vendor component files (.s2p), **When** user selects "Import Component Library" and chooses the folder, **Then** system parses all .s2p files and extracts component metadata (manufacturer, part number, component type: capacitor or inductor, value/range).
2. **Given** library imported, **When** user searches for "capacitor 10pF", **Then** system displays all matching components with key parameters (frequency range, impedance at center frequency, insertion loss estimate).
3. **Given** component library loaded, **When** user selects a component, **Then** system previews its S-parameters on a secondary Smith Chart for validation before use.

---

### User Story 3 - Automatic Matching Network Optimization (Priority: P1)

**Why this priority**: Manual tuning of matching networks is error-prone and time-consuming. Automatic optimization targeting Smith Chart center with minimum line circle is the core value proposition—RF engineers can iterate quickly and validate designs.

**Independent Test**: Can automatically compute a matching network (combination of vendor components) that brings the main device impedance to Smith Chart center (50Ω target) across the specified frequency range, with visualization of the optimization result.

**Acceptance Scenarios**:

1. **Given** main device file loaded and component library imported, **When** user selects topology (L-section series→parallel, Pi-section parallel→series, or T-section) and frequency range, then clicks "Auto-Optimize", **Then** system uses grid search to enumerate all vendor component combinations for the selected topology that minimize reflection coefficient at center frequency.
2. **Given** optimization completes, **When** user views results, **Then** system displays optimized impedance on Smith Chart (should be at or near center), shows selected component values and topology, and displays return loss (S11) before and after matching.
3. **Given** optimization result displayed, **When** user applies the solution, **Then** system cascades the three S-parameter files (main device + matching stages) and validates new combined S-parameters show impedance near 50Ω ± 5Ω across frequency band.

---

### User Story 4 - Interactive GUI with Smith Chart Visualization (Priority: P2)

**Why this priority**: Visual feedback on Smith Chart is essential for RF engineers to understand impedance transformations. A user-friendly GUI enables rapid iteration and validation without command-line friction.

**Independent Test**: Can display main device impedance trajectory on Smith Chart, overlay matching network impedance circles, and allow user to click-to-select frequency points. GUI responds to file loads and optimization without crashes.

**Acceptance Scenarios**:

1. **Given** main file loaded, **When** user views Smith Chart tab, **Then** impedance trajectory is drawn as a curve from start to end frequency, color-coded by frequency (rainbow or gradient).
2. **Given** optimization applied, **When** user toggles "Show Matching Network" checkbox, **Then** additional circles/arcs appear showing impedance at each matching stage (before matching, after L-match, after final stage).
3. **Given** two Smith Charts visible (before/after), **When** user hovers over a frequency point on one chart, **Then** corresponding frequency is highlighted on both charts simultaneously for correlation.

---

### User Story 5 - Multi-Frequency Bandwidth Optimization (Priority: P2)

**Why this priority**: Real RF systems must maintain good matching across a frequency range (not just single frequency). Engineers need to optimize the "line circle" (bandwidth) while keeping center close to 50Ω.

**Independent Test**: Can compute matching network that optimizes reflection coefficient (or VSWR) across entire frequency band, not just center frequency, with trade-offs visible (flat response vs. narrow-band peaks).

**Acceptance Scenarios**:

1. **Given** frequency range selected (e.g., 2.4–2.5 GHz), **When** user clicks "Optimize Bandwidth", **Then** system computes matching network using vendor components that minimizes maximum VSWR or maximum reflection across band (Chebyshev-like ripple or maximally flat).
2. **Given** optimization complete, **When** user views results, **Then** system displays VSWR curve across frequency band (should be < 2.0 across band if successful) and highlights "line circle" radius on Smith Chart.
3. **Given** multiple optimization results (narrow-band vs. wide-band), **When** user compares solutions side-by-side, **Then** trade-offs are clear: single-frequency tighter matching vs. bandwidth flatter response.

---

### Edge Cases

- What happens when user loads an invalid or corrupted .snp file (malformed data, missing header)?
- How does system handle component library with overlapping part numbers or ambiguous naming (e.g., multiple "10pF" capacitors from different manufacturers)?
- What if no matching network solution exists within available components (impedance outside reachable region)?
- How does system handle .snp files with different formats or non-standard frequency spacing?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept .snp files (S1P, S2P, S3P, S4P) as main device input. For multi-port files (S3P/S4P), user specifies source port and load port (e.g., "Port 1 → Port 2") via port selection dialog; system extracts the 2×2 submatrix for matching. Parse frequency, S-parameter data, and port impedance (default 50Ω).
- **FR-002**: System MUST accept folder of vendor .s2p component files (S2P format), extract metadata (part number, component type, impedance model, frequency grid), and catalog by component type.
- **FR-003**: System MUST implement automatic matching network optimizer using grid search that enumerates all vendor component combinations and topology orderings. User selects topology (L-section series→parallel, Pi-section parallel→series, T-section, or custom) before optimization; system searches all valid component combinations for selected topology to minimize reflection coefficient at center frequency.
- **FR-004**: System MUST cascade S-parameter files (main device + matching stages) using standard ABCD matrix chain multiplication and verify final combined S-parameters.
- **FR-005**: System MUST display main device and optimized impedance on Smith Chart with frequency-color overlay and interactive frequency selection.
- **FR-006**: System MUST compute and display VSWR, reflection coefficient (|S11|), and return loss (in dB) at all frequency points.
- **FR-007**: System MUST export optimized matching network schematic (component list with values) and combined .s2p file (main device + matching stages cascaded).
- **FR-008**: System MUST validate that selected components have S-parameter data at all required frequencies (no gaps or extrapolation). If a component is missing any frequency point in the main device's frequency grid, system MUST reject the component with a warning dialog showing which frequencies are missing. This ensures data integrity and prevents hidden interpolation errors.
- **FR-009**: System MUST support undo/redo for optimization iterations and component selection changes.
- **FR-010**: System MUST allow user to manually override automatic selection (e.g., force specific component or limit topology to series-only, shunt-only).

### Key Entities *(include if feature involves data)*

- **SNP File**: Represents S-parameters of a device at discrete frequency points; parsed into frequency array, S-matrix per frequency, and source/load impedance.
- **Component Model**: Vendor S2P file for a single passive component (capacitor or inductor); includes S-parameters, part number, component type, nominal value/range.
- **Matching Network**: Collection of 1–3 passive components arranged in series/parallel topology; characterized by S-parameters (cascade result) and schematic netlist.
- **Smith Chart Point**: Impedance (complex or polar) at a specific frequency; maps to visual location on Smith Chart normalized to 50Ω.
- **Optimization Result**: Solution containing selected components, topology, combined S-parameters, and quality metrics (return loss, VSWR, bandwidth).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can load a main device .snp file and view S-parameters within 2 seconds; GUI displays no lag or blocking.
- **SC-002**: User can import a folder with 50+ vendor component files and search/filter within 1 second per query; library is fully indexed.
- **SC-003**: Auto-optimization returns a matching solution within 5 seconds for single-frequency optimization; multi-frequency bandwidth optimization within 30 seconds.
- **SC-004**: Optimized matching network achieves impedance within 50Ω ± 10Ω (or VSWR < 2.0) at center frequency and maintains < 3.0 VSWR across specified bandwidth in 90% of test cases (typical RF devices).
- **SC-005**: User can visualize impedance trajectory on Smith Chart with real-time frequency cursor; no visual artifacts or rendering delays.
- **SC-006**: Exported .s2p file (cascaded main device + matching stages) can be imported back and yields identical S-parameters (within numerical precision, e.g., 0.1 dB) when re-analyzed.
- **SC-007**: User satisfaction: 80% of beta users successfully complete a matching optimization without consulting documentation (intuitive workflow).

### Assumptions

- **Assumption-A1**: Main device .snp file uses standard Touchstone format (frequency in Hz or GHz, S-parameters in dB/angle or linear/phase, or real/imaginary).
- **Assumption-A2**: Vendor .s2p files are well-formed S2P Touchstone format with consistent frequency grids (engineers typically have curated libraries).
- **Assumption-A3**: Target impedance is 50Ω (industry standard for RF/microwave); system assumes 50Ω reference unless file specifies otherwise.
- **Assumption-A4**: Matching network is passive (no active devices, amplifiers, or attenuators); components are ideal (lossless) or include measured loss in S-parameters.
- **Assumption-A5**: Optimization targets reflection coefficient or VSWR (no gain, noise figure, or linearity constraints); future phases may add multi-objective optimization.

---

## Additional Notes

- **Design Kit Context**: Murata and TDK provide free design kits (S2P files) for capacitors and inductors; system should support import from raw or structured folders.
- **Smith Chart Conventions**: Use normalized Smith Chart (50Ω reference). Plot impedance locus at all frequencies; overlay matching network impedance circles for visual feedback.
- **Numerical Stability**: Cascade matrices may have numerical issues if frequencies have large gaps or components have extreme impedance values; document any limitations.
- **Future Enhancements** (out of scope for MVP): transmission line matching, multi-element networks (>3 stages), lossy components with noise/stability analysis, fabrication-aware component selection.

## Clarifications

### Session 2025-11-26

- **Q1: Optimization Algorithm Choice** → **A: Grid Search (brute-force enumeration)**. Enumerates all vendor component combinations for the selected topology. Deterministic, fits 5–30 sec performance targets, MVP-aligned, and ensures optimal solution within topology.

- **Q2: Multi-Port Device Handling (S3P/S4P)** → **A: Manual Port Selection**. User specifies source port and load port (e.g., "Port 1 → Port 2") via dialog when loading multi-port files. System extracts the 2×2 submatrix for matching. Simple, matches RF engineer workflow, avoids wrong assumptions.

- **Q3: Matching Network Topology Flexibility** → **A: Flexible Topology Selection**. Engineer chooses from preset topologies (L-section series→parallel, Pi-section parallel→series, T-section, or custom) before optimization. Grid search enumerates topologies for the same components. Slightly larger search space (~2× permutations); grid search still MVP-feasible. Enables best RF solution per device.

- **Q4: Component Frequency Coverage Gap Handling** → **A: Reject with Warning**. If component has missing frequencies in the main device's frequency grid, reject component and show user which frequencies are missing. Ensures data integrity, avoids hidden interpolation, encourages selecting complete-coverage components.

