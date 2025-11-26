# Contract: Grid Search Optimizer

**Module**: `snp_tool.optimizer.grid_search`  
**Purpose**: Implement grid search algorithm to find optimal matching network

---

## Class: `GridSearchOptimizer`

**Constructor**: `__init__(device: SNPFile, component_library: list[ComponentModel])`

**Input**:
- `device`: SNPFile (main device to be matched)
- `component_library`: List of ComponentModel objects (filtered by frequency coverage)

**Attributes**:
- `device`: Reference to input device
- `components`: Reference to component library
- `search_iterations`: Counter for benchmarking

---

## Method: `optimize(topology: str, frequency_range: tuple, target_frequency: float = None) -> OptimizationResult`

**Input**:
- `topology`: String in ('L-section', 'Pi-section', 'T-section')
- `frequency_range`: Tuple (start_freq, end_freq) in Hz
- `target_frequency`: (optional) Single frequency to optimize at; default: midpoint of range

**Output**: `OptimizationResult` object (see data-model.md)

**Algorithm**:
1. Validate component library has full frequency coverage within `frequency_range` (reject components with gaps per Q4)
2. Determine number of components per topology:
   - L-section: 2 components (series + shunt)
   - Pi-section: 2 components (shunt + series)
   - T-section: 3 components (series + shunt + series)
3. Enumerate all combinations:
   - For each component slot 1: 50 options (all capacitors + inductors in library)
   - For each component slot 2: 50 options
   - (For T-section: For each slot 3: 50 options)
   - Total: ~50^(num_slots) combinations
4. For each combination:
   a. Build matching network (assign components to topology)
   b. Cascade S-parameters using ABCD matrices (main device + component1 + component2)
   c. Calculate reflection coefficient at `target_frequency`: |S11(target_freq)|
   d. Track best solution (minimum reflection)
5. Return OptimizationResult with best solution

**Raises**:
- `InsufficientComponentCoverageError`: Components missing frequencies required for optimization
- `NoSolutionFoundError`: No combination achieves target impedance
- `TopologyError`: Invalid topology name

**Example**:
```python
optimizer = GridSearchOptimizer(device, library)
result = optimizer.optimize(
    topology='L-section',
    frequency_range=(2.0e9, 2.5e9),
    target_frequency=2.25e9
)
print(f"Best components: {result.matching_network.components}")
print(f"Reflection coeff: {result.optimization_metrics['reflection_coefficient_at_center']}")
```

---

## Method: `get_reflection_coefficient(component1: ComponentModel, component2: ComponentModel, topology: str, frequency: float) -> float`

**Input**:
- `component1`: First component
- `component2`: Second component
- `topology`: Topology string
- `frequency`: Frequency point to evaluate at

**Output**: |S11| (magnitude of reflection coefficient, 0–1)

**Algorithm**:
1. Build S-parameter matrix for component1 (read from .s2p)
2. Build S-parameter matrix for component2 (read from .s2p)
3. Cascade with main device using topology:
   - L-section: main device → series component1 → shunt component2 → 50Ω load
   - Pi-section: main device → shunt component1 → series component2 → 50Ω load
   - (See ABCD cascading below)
4. Extract S11 at specified frequency
5. Return |S11|

---

## Class: `ABCDCascader` (Helper)

**Purpose**: Cascade S-parameter matrices using ABCD transmission line parameters

**Method**: `cascade(s_params_list: list[dict], topology: str) -> dict`

**Input**:
- `s_params_list`: List of S-parameter dicts from components in order
- `topology`: How to connect (series vs. shunt per topology)

**Algorithm**:
1. Convert each S-parameter matrix to ABCD matrix
2. For series components: Connect in cascade (multiply ABCD matrices)
3. For shunt components: Create shunt network equivalent
4. Multiply all ABCD matrices in sequence
5. Convert result back to S-parameters
6. Return cascaded S-parameter dict

**Validates**: All frequency grids align (no extrapolation)

---

## Performance Notes

- **Search Space**: ~50 components × 2–3 slots = 2,500–125,000 combinations
- **Target**: < 5 sec for single-frequency, < 30 sec for multi-frequency
- **Optimization**: Vectorize with numpy for speed; avoid loops where possible
- **Benchmarking**: Log iterations, timing per combination

**Example Timing** (estimated):
- Load device.s2p (100 freq points): 50 ms
- Cascade per combination: 10 ms
- Single-freq optimize (100 combinations): 1.0 sec
- Multi-freq optimize (10 bands, 100 freq points, 100 combinations): 10 sec

