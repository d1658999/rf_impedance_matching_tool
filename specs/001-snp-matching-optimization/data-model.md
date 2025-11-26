# Data Model: SNP File Matching Optimization

**Created**: 2025-11-26  
**Phase**: 1 (Design)  
**Status**: Complete

---

## Entities & Relationships

### 1. SNP File

**Purpose**: Represents S-parameters of a device (main device being matched) at discrete frequency points.

**Fields**:
- `file_path`: str (path to .snp file)
- `frequency`: ndarray[float] (frequency points in Hz; from file header or calculated)
- `s_parameters`: dict[str, ndarray[complex]] (S-matrix per frequency; e.g., 's11', 's12', 's21', 's22' for 2-port)
- `num_ports`: int (1, 2, 3, or 4)
- `source_port_index`: int (0-indexed port number; default 0 for S1P/S2P)
- `load_port_index`: int (0-indexed port number; default 1 for S2P, or user-selected for S3P/S4P)
- `reference_impedance`: float (default 50.0 Ω)
- `frequency_unit`: str ('Hz', 'kHz', 'MHz', 'GHz'; parsed from file)
- `s_parameter_format`: str ('dB/angle', 'linear/phase', 'real/imaginary'; parsed from file)
- `center_frequency`: float (calculated as mean of frequency array)
- `impedance_at_frequency`: function(frequency) → complex (calculated from S11 at given freq)

**Validation Rules**:
- frequency array must be sorted ascending and monotonic (no duplicates)
- s_parameters must have same length as frequency array
- source_port_index and load_port_index must be valid (0 ≤ index < num_ports)
- reference_impedance > 0

**State Transitions**:
- Created (loaded from file) → Parsed (S-parameters extracted) → Ready (impedance computed)

**Example**:
```python
snp_file = SNPFile(
    file_path="device.s2p",
    frequency=array([2.0e9, 2.1e9, ..., 2.5e9]),  # 51 points
    s_parameters={'s11': [...], 's12': [...], 's21': [...], 's22': [...]},
    num_ports=2,
    source_port_index=0,
    load_port_index=1,
    reference_impedance=50.0,
    center_frequency=2.25e9
)
# Impedance at 2.3 GHz: snp_file.impedance_at_frequency(2.3e9) → (45.2 + 5.3j) Ω
```

---

### 2. Component Model

**Purpose**: Represents a single vendor passive component (capacitor or inductor) with S-parameters.

**Fields**:
- `s2p_file_path`: str (path to vendor .s2p file)
- `manufacturer`: str (e.g., 'Murata', 'TDK')
- `part_number`: str (e.g., 'GRM155R61A105KA01L')
- `component_type`: str ('capacitor' or 'inductor'; derived from S-parameters or metadata)
- `value`: str (e.g., '10pF', '1nH') or None (derived from S-parameters if not in metadata)
- `value_nominal`: float (in Farads for capacitor, Henries for inductor; None if unknown)
- `frequency`: ndarray[float] (frequency points where S-parameters are defined)
- `frequency_grid`: list[float] (sorted, unique frequency points; used for coverage validation)
- `s_parameters`: dict[str, ndarray[complex]] (S11, S12, S21, S22 per frequency)
- `reference_impedance`: float (typically 50.0 Ω)
- `impedance_at_frequency`: function(frequency) → complex (calculated from S11)
- `metadata`: dict (optional; manufacturer-supplied info, measurement conditions, etc.)

**Validation Rules**:
- frequency_grid must not have gaps (no missing frequency points within range)
- s_parameters length must match frequency length
- component_type in ('capacitor', 'inductor')
- value_nominal > 0 if specified

**Special Handling (Q4 Clarification)**:
- If frequency_grid does NOT fully overlap with main device's frequency_grid → component is **rejected**
- Warning: "Component {part_number} is missing frequencies: {missing_freqs}"

**Example**:
```python
component = ComponentModel(
    s2p_file_path="Murata/GRM155R61A105KA01L.s2p",
    manufacturer="Murata",
    part_number="GRM155R61A105KA01L",
    component_type="capacitor",
    value="10pF",
    value_nominal=1e-11,  # 10e-12 Farads
    frequency=array([100e6, 200e6, ..., 6e9]),  # 59 points
    frequency_grid=[100e6, 200e6, ..., 6e9],
    reference_impedance=50.0
)
# Impedance at 2.4 GHz: component.impedance_at_frequency(2.4e9) → (complex value)
```

---

### 3. Matching Network

**Purpose**: Represents the optimized 2-stage matching network (solution) connecting main device to 50Ω load.

**Fields**:
- `components`: list[ComponentModel] (1–3 components, ordered)
- `topology`: str ('L-section', 'Pi-section', 'T-section', or custom)
  - L-section: series-then-parallel (series L/C, then shunt L/C)
  - Pi-section: parallel-then-series (shunt L/C, then series L/C)
  - T-section: series-shunt-series (3 components)
- `component_order`: list[str] (['series', 'shunt'] or ['shunt', 'series'] or ['series', 'shunt', 'series'])
- `cascaded_s_parameters`: dict[str, ndarray[complex]] (S11, S12, S21, S22 after cascading)
- `frequency`: ndarray[float] (frequency points for cascaded S-params; same as main device)
- `impedance_at_frequency`: function(frequency) → complex (impedance after matching)
- `schematic`: str (text representation; e.g., "Source → L(1nH) → C(10pF) → 50Ω load")

**Derived Metrics**:
- `reflection_coefficient_at_frequency`: function(freq) → float (|S11| at freq)
- `vswr_at_frequency`: function(freq) → float ((1 + |S11|) / (1 - |S11|))
- `return_loss_at_frequency`: function(freq) → float (-20 * log10(|S11|) in dB)
- `center_frequency_impedance`: complex (impedance at main device center frequency)
- `max_vswr_in_band`: float (worst VSWR across frequency band)
- `bandwidth_vswr_lt_2`: float (frequency range where VSWR < 2.0)

**Validation Rules**:
- 1 ≤ len(components) ≤ 3
- All components in network must have frequency coverage matching main device (no gaps)
- cascaded_s_parameters derived from components + topology via ABCD cascade

**Example**:
```python
matching_network = MatchingNetwork(
    components=[capacitor_10pf, inductor_1nh],
    topology='L-section',
    component_order=['series', 'shunt'],
    cascaded_s_parameters={...},  # computed via ABCD cascade
    frequency=array([2.0e9, 2.1e9, ..., 2.5e9])
)
# Impedance after matching at center freq: (50.2 + 0.3j) Ω
# VSWR at center freq: 1.006
# Return loss at center freq: 46.4 dB
```

---

### 4. Optimization Result

**Purpose**: Represents the complete solution returned by the optimizer.

**Fields**:
- `matching_network`: MatchingNetwork (the optimized network)
- `main_device`: SNPFile (input device being matched)
- `component_library`: list[ComponentModel] (components used in search)
- `topology_selected`: str ('L-section', 'Pi-section', or 'T-section')
- `frequency_range`: tuple[float, float] ((start_freq, end_freq) in Hz used for optimization)
- `optimization_target`: str ('single-frequency' or 'bandwidth')
- `center_frequency`: float (frequency optimized at, or midpoint of bandwidth)
- `optimization_metrics`: dict (results of optimization)
  - `reflection_coefficient_at_center`: float (|S11| at center frequency)
  - `vswr_at_center`: float (VSWR at center frequency)
  - `return_loss_at_center_dB`: float (return loss in dB)
  - `max_vswr_in_band`: float (worst VSWR across band)
  - `grid_search_iterations`: int (number of component combinations evaluated)
  - `grid_search_duration_sec`: float (computation time)
- `success`: bool (True if impedance within 50Ω ± 10Ω or VSWR < 2.0 at center)
- `export_formats`: dict (paths to exported files)
  - `schematic_txt`: str (path to component list)
  - `s_parameters_s2p`: str (path to cascaded .s2p file)

**Example**:
```python
result = OptimizationResult(
    matching_network=matching_network,
    main_device=snp_file,
    topology_selected='L-section',
    frequency_range=(2.0e9, 2.5e9),
    optimization_target='single-frequency',
    center_frequency=2.25e9,
    optimization_metrics={
        'reflection_coefficient_at_center': 0.095,
        'vswr_at_center': 1.21,
        'return_loss_at_center_dB': 20.4,
        'max_vswr_in_band': 1.85,
        'grid_search_iterations': 10000,
        'grid_search_duration_sec': 4.2
    },
    success=True,
    export_formats={
        'schematic_txt': 'results/solution_schematic.txt',
        's_parameters_s2p': 'results/cascaded_device.s2p'
    }
)
```

---

### 5. Component Library (Catalog)

**Purpose**: Searchable index of imported vendor component files.

**Fields**:
- `library_path`: str (folder path containing .s2p files)
- `index`: dict[str, list[ComponentModel]] (indexed by (type, value) tuples)
- `components_by_manufacturer`: dict[str, list[ComponentModel]]
- `components_by_type`: dict[str, list[ComponentModel]] ('capacitor', 'inductor')
- `frequency_coverage`: dict[str, tuple[float, float]] (per part_number: (min_freq, max_freq))
- `last_indexed`: datetime (timestamp of last folder scan)

**Methods**:
- `search(query: str)` → list[ComponentModel] (search by type, value, part_number, manufacturer)
- `get_by_type_and_value(type: str, value_str: str)` → list[ComponentModel]
- `validate_frequency_coverage(frequency_grid: list[float])` → list[ComponentModel] (returns components with full coverage)

**Example**:
```python
library = ComponentLibrary(library_path="vendor_kits/")
library.index_folder()  # Scan and parse all .s2p files

# Search for 10pF capacitors
results = library.search("capacitor 10pF")  # → 5 manufacturers

# Validate which components span 2.0–2.5 GHz
valid = library.validate_frequency_coverage(device_frequency_grid)  # → 45 of 50 components valid
```

---

## Database Schema (if persistence needed in future)

*Note: MVP uses file-based JSON caching; full database optional for Phase 2+.*

### Components Table
```sql
CREATE TABLE components (
    id INTEGER PRIMARY KEY,
    s2p_file_path TEXT UNIQUE NOT NULL,
    manufacturer TEXT NOT NULL,
    part_number TEXT NOT NULL,
    component_type TEXT NOT NULL,  -- 'capacitor' or 'inductor'
    value_nominal REAL,  -- in Farads (capacitor) or Henries (inductor)
    frequency_min REAL,
    frequency_max REAL,
    reference_impedance REAL DEFAULT 50.0,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_type_value ON components(component_type, value_nominal);
CREATE INDEX idx_manufacturer ON components(manufacturer);
```

### SNP Files Table (optional)
```sql
CREATE TABLE snp_files (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    num_ports INTEGER,
    frequency_min REAL,
    frequency_max REAL,
    num_frequency_points INTEGER,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Optimization Results Table (optional)
```sql
CREATE TABLE optimization_results (
    id INTEGER PRIMARY KEY,
    device_id INTEGER REFERENCES snp_files(id),
    topology TEXT,
    center_frequency REAL,
    reflection_coefficient_at_center REAL,
    vswr_at_center REAL,
    components_json TEXT,  -- JSON array of component part numbers
    optimized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES snp_files(id)
);
```

---

## Relationships Diagram

```
SNPFile
  ├─ source_port_index → (port in file)
  ├─ load_port_index → (port in file)
  └─ impedance_at_frequency() → complex

ComponentModel
  ├─ frequency_grid (validation for matching)
  └─ impedance_at_frequency() → complex

MatchingNetwork
  ├─ components[] → list[ComponentModel]
  ├─ topology → ('L-section', 'Pi-section', 'T-section')
  └─ cascaded_s_parameters (derived from components + topology)

OptimizationResult
  ├─ matching_network → MatchingNetwork
  ├─ main_device → SNPFile
  ├─ component_library → list[ComponentModel]
  └─ optimization_metrics → dict

ComponentLibrary
  ├─ components[] → list[ComponentModel]
  └─ index → dict[tuple, list[ComponentModel]]
```

---

## Key Validations

| Rule | Entity | Check |
|------|--------|-------|
| No frequency gaps in SNPFile | SNPFile | frequency array is sorted, monotonic |
| Component frequency coverage | ComponentModel | no gaps within range used for matching |
| Topology component count | MatchingNetwork | 1–3 components, ordered per topology |
| Cascaded S-parameters valid | MatchingNetwork | 2×2 complex matrix, causality preserved (if needed) |
| Success criteria met | OptimizationResult | impedance within 50Ω ± 10Ω or VSWR < 2.0 |
| Export files generated | OptimizationResult | schematic_txt and s_parameters_s2p paths exist |

