# Data Model: RF Impedance Matching Optimizer

**Phase**: 1 (Design & Contracts)  
**Date**: 2025-11-27  
**Input**: Key Entities from spec.md, research.md technology decisions

## Overview

This document defines the complete data model for the RF Impedance Matching Optimizer, including entities, relationships, validation rules, and state machines.

---

## Entities

### 1. SParameterNetwork

**Description**: Represents an RF network characterized by frequency-dependent scattering parameters loaded from SNP files or modified by component additions.

**Fields**:
```python
@dataclass
class SParameterNetwork:
    """S-Parameter Network entity."""
    
    filepath: Path                          # Original SNP file path
    port_count: int                         # Number of ports (1-4 initially, extensible to 8/16)
    frequencies: np.ndarray                 # Frequency points in Hz (shape: [N])
    s_parameters: np.ndarray                # Complex S-parameters (shape: [N, port_count, port_count])
    impedance_normalization: float          # Characteristic impedance (default: 50.0 ohms)
    frequency_unit: str                     # Original file frequency unit ('Hz', 'MHz', 'GHz')
    format_type: str                        # SNP format ('RI', 'MA', 'DB')
    loaded_at: datetime                     # Timestamp of file load
    checksum: str                           # MD5 checksum of original file
    
    # Computed properties (cached)
    _impedance_matrix: Optional[np.ndarray] = None  # Z-parameters (lazy computed)
    _admittance_matrix: Optional[np.ndarray] = None  # Y-parameters (lazy computed)
```

**Relationships**:
- Has many `FrequencyPoint` (1:N, computed from frequencies and s_parameters)
- Has many `PortConfiguration` (1:N, one per port)

**Validation Rules** (from FR-001, FR-013):
- `port_count` must match S-parameter matrix dimensions: `s_parameters.shape[1] == s_parameters.shape[2] == port_count`
- `frequencies` must be monotonically increasing: `all(frequencies[i] < frequencies[i+1])`
- `frequencies.shape[0] == s_parameters.shape[0]` (matching number of frequency points)
- `impedance_normalization > 0` (must be positive real number)
- `frequency_unit` in ['Hz', 'kHz', 'MHz', 'GHz']
- `format_type` in ['RI', 'MA', 'DB'] (Real/Imaginary, Magnitude/Angle, dB/Angle)

**State Transitions**:
```
loaded (initial) → modified (components added) → optimized (optimization run) → exported
```

**Methods**:
```python
def get_impedance_at_frequency(self, freq_hz: float, port: int) -> complex:
    """Calculate input impedance at specific frequency and port."""
    
def get_frequency_point(self, index: int) -> FrequencyPoint:
    """Get FrequencyPoint object for specific index."""
    
def to_scikit_rf_network(self) -> skrf.Network:
    """Convert to scikit-rf Network object for calculations."""
```

---

### 2. MatchingComponent

**Description**: Represents a lumped element (capacitor or inductor) with specific value and placement configuration, assigned to a port for impedance transformation.

**Fields**:
```python
from enum import Enum

class ComponentType(Enum):
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"

class PlacementType(Enum):
    SERIES = "series"
    SHUNT = "shunt"

@dataclass
class MatchingComponent:
    """Matching Component entity."""
    
    id: str                                 # Unique identifier (UUID)
    port: int                               # Port number (1-indexed)
    component_type: ComponentType           # Capacitor or Inductor
    value: float                            # Component value in base units (Farads or Henrys)
    placement: PlacementType                # Series or shunt configuration
    created_at: datetime                    # Timestamp of creation
    order: int = 0                          # Order in cascade (0=first, 1=second, etc.)
    
    # Display properties
    @property
    def value_display(self) -> str:
        """Engineering notation display (e.g., '10pF', '5nH')."""
        from snp_tool.utils.engineering import format_engineering_notation
        unit = 'F' if self.component_type == ComponentType.CAPACITOR else 'H'
        return format_engineering_notation(self.value, unit)
```

**Relationships**:
- Belongs to `PortConfiguration` (N:1)
- May be part of `OptimizationSolution` (N:M, many-to-many)

**Validation Rules** (from FR-003, FR-005, physical constraints):
- `port >= 1` and `port <= network.port_count`
- `value > 0` (must be positive)
- **Capacitor range**: `1e-15 <= value <= 1e-4` (1fF to 100µF)
- **Inductor range**: `1e-12 <= value <= 1e-1` (1pH to 100mH)
- `order >= 0` and `order < 5` (max 5 components per port)

**Constraints**:
- Maximum 5 components per port (FR-003)
- Component values must be physically realizable
- In standard-value mode (FR-016): value must be from E12/E24/E96 series

**Methods**:
```python
def to_dict(self) -> Dict[str, Any]:
    """Serialize to dictionary for session save."""
    
def to_scikit_rf_network(self, frequencies: np.ndarray, z0: float) -> skrf.Network:
    """Convert to 2-port scikit-rf Network for cascading."""
    
@staticmethod
def from_engineering_notation(port: int, comp_type: str, value_str: str, placement: str) -> 'MatchingComponent':
    """Create from engineering notation string (e.g., '10pF')."""
```

---

### 3. PortConfiguration

**Description**: Represents the state of a single port including its reference impedance, added components, and current impedance characteristics.

**Fields**:
```python
@dataclass
class PortConfiguration:
    """Port Configuration entity."""
    
    port_number: int                        # Port number (1-indexed)
    reference_impedance: float              # Reference Z0 (typically 50 or 75 ohms)
    components: List[MatchingComponent]     # Components added to this port (max 5)
    
    # Current state (recomputed when components change)
    current_impedance: Optional[complex] = None  # Input impedance after components
    vswr: Optional[float] = None            # VSWR at center frequency
    return_loss_db: Optional[float] = None  # Return loss in dB
```

**Relationships**:
- Belongs to `SParameterNetwork` (N:1)
- Has many `MatchingComponent` (1:N, ordered by `order` field)

**Validation Rules**:
- `port_number >= 1`
- `reference_impedance > 0`
- `len(components) <= 5` (FR-003 constraint)
- Components must have unique `order` values within same port

**Methods**:
```python
def add_component(self, component: MatchingComponent) -> None:
    """Add component, validating max 5 constraint."""
    
def remove_component(self, component_id: str) -> None:
    """Remove component by ID."""
    
def get_cascaded_network(self, frequencies: np.ndarray) -> skrf.Network:
    """Get cascaded network with all components applied."""
    
def calculate_metrics(self, target_impedance: float = 50.0) -> Dict[str, float]:
    """Calculate VSWR, return loss, reflection coefficient."""
```

---

### 4. FrequencyPoint

**Description**: Represents a single frequency value with associated S-parameters and impedance values for all ports.

**Fields**:
```python
@dataclass
class FrequencyPoint:
    """Frequency Point entity."""
    
    frequency_hz: float                     # Frequency in Hz
    s_parameters: np.ndarray                # S-parameters at this frequency (shape: [port_count, port_count])
    
    # Computed impedance values per port
    impedances: Dict[int, complex]          # {port_number: impedance} mapping
    vswr_values: Dict[int, float]           # {port_number: VSWR} mapping
    return_loss_db: Dict[int, float]        # {port_number: return_loss} mapping
```

**Relationships**:
- Belongs to `SParameterNetwork` (N:1)

**Methods**:
```python
def get_impedance(self, port: int) -> complex:
    """Get impedance for specific port."""
    
def get_reflection_coefficient(self, port: int, z0: float = 50.0) -> complex:
    """Calculate reflection coefficient Gamma."""
```

---

### 5. OptimizationSolution

**Description**: Represents a complete impedance matching solution with component values, port assignments, and performance metrics.

**Fields**:
```python
@dataclass
class OptimizationSolution:
    """Optimization Solution entity."""
    
    id: str                                 # Unique solution ID
    components: List[MatchingComponent]     # Matched components (up to 5 per port)
    metrics: Dict[str, float]               # Performance metrics
    score: float                            # Weighted objective score (lower is better)
    mode: str                               # 'ideal' or 'standard_values'
    target_impedance: float                 # Target impedance used
    frequency_range: Tuple[float, float]    # (min_hz, max_hz) optimization range
    created_at: datetime                    # Timestamp
    
    # Detailed metrics
    @property
    def return_loss_db(self) -> float:
        return self.metrics.get('return_loss_db', 0.0)
    
    @property
    def vswr(self) -> float:
        return self.metrics.get('vswr', float('inf'))
    
    @property
    def bandwidth_hz(self) -> float:
        return self.metrics.get('bandwidth_hz', 0.0)
    
    @property
    def component_count(self) -> int:
        return len(self.components)
```

**Relationships**:
- References `SParameterNetwork` (via optimization context)
- Has many `MatchingComponent` (1:N, solution-specific instances)

**Validation Rules**:
- `score >= 0` (non-negative cost function)
- `target_impedance > 0`
- `frequency_range[0] < frequency_range[1]`
- `mode` in ['ideal', 'standard_values']

**Ranking Logic** (FR-009):
- Solutions sorted by `score` (ascending: lower score = better solution)
- Tie-breaker: fewer components preferred

**Methods**:
```python
def apply_to_network(self, network: SParameterNetwork) -> SParameterNetwork:
    """Apply this solution's components to network."""
    
def export_to_dict(self) -> Dict[str, Any]:
    """Export solution for session save or export file."""
```

---

### 6. WorkSession

**Description**: Represents a saved design state including SNP file reference, all matching components, optimization settings, and GUI state.

**Fields**:
```python
@dataclass
class WorkSession:
    """Work Session entity."""
    
    version: str                            # Session format version (e.g., '1.0')
    created_at: datetime
    last_modified: datetime
    tool_version: str                       # snp-tool version that created session
    
    # SNP file reference
    snp_file_path: Path                     # Original SNP file path
    snp_file_checksum: str                  # MD5 checksum for integrity check
    
    # Network state
    network: Optional[SParameterNetwork] = None  # Loaded network (transient, not serialized)
    components: List[MatchingComponent]     # All components added
    
    # Optimization state
    optimization_config: Dict[str, Any]     # {target_impedance, weights, mode, series, etc.}
    best_solution: Optional[OptimizationSolution] = None
    
    # GUI state (optional, GUI-specific)
    gui_state: Optional[Dict[str, Any]] = None  # {selected_plot, zoom, window_geometry}
```

**Relationships**:
- References `SParameterNetwork` (via snp_file_path)
- Has many `MatchingComponent` (1:N, all components in session)
- May have `OptimizationSolution` (1:1, best solution found)

**Validation Rules** (FR-020, FR-021):
- `version` must match current SESSION_VERSION or be migratable
- `snp_file_path` must be valid Path (existence checked on load)
- If `network` loaded, checksum must match `snp_file_checksum`

**State Transitions**:
```
created (new session) → modified (components added/removed) → optimized (optimization run) → saved (persisted to file)
```

**Methods**:
```python
def save_to_file(self, filepath: Path) -> None:
    """Save session to JSON file."""
    from snp_tool.utils.session_io import save_session
    save_session(filepath, self.to_dict())

def load_network(self) -> SParameterNetwork:
    """Load referenced SNP file and validate checksum."""
    
def verify_snp_file_integrity(self) -> bool:
    """Check if SNP file matches saved checksum."""
    
@staticmethod
def load_from_file(filepath: Path) -> 'WorkSession':
    """Load session from JSON file."""
```

---

## Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     SParameterNetwork                           │
│  - filepath, port_count, frequencies, s_parameters              │
│  - impedance_normalization, loaded_at, checksum                 │
└────────┬─────────────────────────────┬──────────────────────────┘
         │ 1:N                          │ 1:N
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌────────────────────────┐
│  FrequencyPoint  │          │  PortConfiguration     │
│  - frequency_hz  │          │  - port_number         │
│  - s_parameters  │          │  - reference_impedance │
│  - impedances    │          │  - components (max 5)  │
└──────────────────┘          └───────────┬────────────┘
                                          │ 1:N (ordered)
                                          │
                                          ▼
                              ┌──────────────────────────┐
                              │   MatchingComponent      │
                              │  - type, value           │
                              │  - placement, order      │
                              │  - port, created_at      │
                              └──────────┬───────────────┘
                                         │ N:M
                                         │
                                         ▼
                              ┌──────────────────────────┐
                              │  OptimizationSolution    │
                              │  - components            │
                              │  - metrics, score        │
                              │  - target_impedance      │
                              └──────────────────────────┘
                                         ▲
                                         │ 1:1 (best solution)
                                         │
                              ┌──────────┴───────────────┐
                              │      WorkSession         │
                              │  - snp_file_path         │
                              │  - components            │
                              │  - optimization_config   │
                              │  - best_solution         │
                              └──────────────────────────┘
```

**Key Relationships**:
1. **SParameterNetwork** → **FrequencyPoint**: 1:N decomposition of frequency-dependent data
2. **SParameterNetwork** → **PortConfiguration**: 1:N (one config per port)
3. **PortConfiguration** → **MatchingComponent**: 1:N ordered list (max 5)
4. **OptimizationSolution** → **MatchingComponent**: N:M (solution contains components)
5. **WorkSession** → **SParameterNetwork**: 1:1 reference via file path
6. **WorkSession** → **OptimizationSolution**: 1:1 (best solution found)

---

## State Machines

### SParameterNetwork State Machine

```
                                    ┌─────────┐
                                    │  LOADED │ (initial state)
                                    └────┬────┘
                                         │
                         add_component() │
                                         ▼
                                  ┌──────────────┐
                                  │   MODIFIED   │
                                  └──────┬───────┘
                                         │
                              optimize() │
                                         ▼
                                  ┌──────────────┐
                                  │  OPTIMIZED   │
                                  └──────┬───────┘
                                         │
                               export()  │
                                         ▼
                                  ┌──────────────┐
                                  │   EXPORTED   │
                                  └──────────────┘

States:
- LOADED: SNP file parsed, no modifications
- MODIFIED: Components added, S-parameters recalculated
- OPTIMIZED: Optimization run, solutions available
- EXPORTED: Results exported to file

Transitions:
- add_component(): LOADED → MODIFIED, MODIFIED → MODIFIED (idempotent)
- optimize(): MODIFIED → OPTIMIZED
- export(): OPTIMIZED → EXPORTED
- load_session(): Any → LOADED (reset)
```

### Component Addition Workflow

```
                           ┌────────────────────┐
                           │  User Input        │
                           │  (type, value,     │
                           │   placement, port) │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │  Parse Engineering │
                           │  Notation (10pF)   │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │  Validate Value    │
                           │  (range, physical) │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │  Check Port Limit  │
                           │  (max 5 per port)  │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │  Create Component  │
                           │  (assign order)    │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │  Cascade to Network│
                           │  (S-param recalc)  │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │  Update Metrics    │
                           │  (VSWR, return loss)│
                           └────────────────────┘
```

### Optimization Workflow State Machine

```
                           ┌────────────────────┐
                           │   IDLE             │ (initial)
                           └─────────┬──────────┘
                                     │ start_optimization()
                                     ▼
                           ┌────────────────────┐
                           │   RUNNING          │
                           │  (iterations)      │
                           └─────────┬──────────┘
                                     │ convergence or max_iter
                                     ▼
                           ┌────────────────────┐
                           │   COMPLETED        │
                           │  (solutions found) │
                           └─────────┬──────────┘
                                     │
                 ┌───────────────────┴────────────────────┐
                 │ apply_solution()                       │ save_session()
                 ▼                                        ▼
      ┌──────────────────┐                    ┌──────────────────┐
      │  SOLUTION_APPLIED│                    │   SESSION_SAVED  │
      │  (network updated)│                    │   (persistent)   │
      └──────────────────┘                    └──────────────────┘

Events:
- start_optimization(): IDLE → RUNNING
- convergence/max_iter: RUNNING → COMPLETED
- apply_solution(): COMPLETED → SOLUTION_APPLIED
- save_session(): SOLUTION_APPLIED → SESSION_SAVED
- reset(): Any → IDLE
```

---

## Validation Rules Summary

| Entity | Validation Rule | Source Requirement |
|--------|-----------------|-------------------|
| SParameterNetwork | port_count matches S-param matrix dims | FR-001 |
| SParameterNetwork | frequencies monotonically increasing | FR-001 |
| SParameterNetwork | impedance_normalization > 0 | FR-013 |
| MatchingComponent | value > 0 | FR-005 |
| MatchingComponent | Capacitor range: 1fF - 100µF | Physical constraint |
| MatchingComponent | Inductor range: 1pH - 100mH | Physical constraint |
| PortConfiguration | Max 5 components per port | FR-003 |
| OptimizationSolution | score >= 0 | Optimization algorithm |
| OptimizationSolution | frequency_range[0] < frequency_range[1] | FR-008 |
| WorkSession | version compatible or migratable | FR-020 edge case |
| WorkSession | SNP file checksum matches on load | FR-020 integrity |

---

## Data Access Patterns

### Create Operations

```python
# Load SNP file
from snp_tool.parsers.touchstone import parse_snp
network = parse_snp(Path("antenna.s2p"))

# Create component
component = MatchingComponent(
    id=str(uuid.uuid4()),
    port=1,
    component_type=ComponentType.CAPACITOR,
    value=10e-12,  # 10pF
    placement=PlacementType.SERIES,
    created_at=datetime.utcnow(),
    order=0
)

# Create port configuration
port_config = PortConfiguration(
    port_number=1,
    reference_impedance=50.0,
    components=[]
)
```

### Read Operations

```python
# Get frequency point
freq_point = network.get_frequency_point(index=50)
impedance = freq_point.get_impedance(port=1)

# Get components for port
port_components = [c for c in all_components if c.port == 1]
port_components.sort(key=lambda c: c.order)  # Cascade order

# Get metrics
metrics = port_config.calculate_metrics(target_impedance=50.0)
vswr = metrics['vswr']
return_loss = metrics['return_loss_db']
```

### Update Operations

```python
# Add component to port
port_config.add_component(component)

# Modify component value
component.value = 15e-12  # Change from 10pF to 15pF
network = apply_component_to_network(network, component)  # Recalculate

# Apply optimization solution
for comp in solution.components:
    port_config.add_component(comp)
```

### Delete Operations

```python
# Remove component
port_config.remove_component(component.id)

# Clear all components from port
port_config.components.clear()

# Reset network to original (reload SNP file)
network = parse_snp(original_filepath)
```

---

## Computed Properties and Caching

### Lazy Computation

Several properties are computationally expensive and should be cached:

```python
class SParameterNetwork:
    @property
    def impedance_matrix(self) -> np.ndarray:
        """Lazy-computed Z-parameters (cached)."""
        if self._impedance_matrix is None:
            skrf_net = self.to_scikit_rf_network()
            self._impedance_matrix = skrf_net.z
        return self._impedance_matrix
    
    def invalidate_cache(self) -> None:
        """Clear cached computed values when network modified."""
        self._impedance_matrix = None
        self._admittance_matrix = None
```

### When to Invalidate Cache

- After adding/removing components: `network.invalidate_cache()`
- After optimization applies solution: `network.invalidate_cache()`
- NOT needed for read-only operations (plot, export)

---

## Serialization Formats

### Component Serialization (JSON)

```json
{
  "id": "comp_abc123",
  "port": 1,
  "component_type": "capacitor",
  "value": 1e-11,
  "value_display": "10.00pF",
  "placement": "series",
  "created_at": "2025-11-27T12:34:56Z",
  "order": 0
}
```

### Solution Serialization (JSON)

```json
{
  "id": "sol_xyz789",
  "components": [
    {"id": "comp_abc123", ...},
    {"id": "comp_def456", ...}
  ],
  "metrics": {
    "return_loss_db": -15.3,
    "vswr": 1.42,
    "bandwidth_hz": 250000000.0
  },
  "score": 0.123,
  "mode": "standard_values",
  "target_impedance": 50.0,
  "frequency_range": [2.0e9, 2.5e9],
  "created_at": "2025-11-27T12:35:00Z"
}
```

### Session Serialization

See `research.md` Section 5 (Session File Format) for complete schema.

---

## Type Hints & Validation

All public methods use Python 3.9+ type hints:

```python
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

def parse_snp(filepath: Path) -> SParameterNetwork:
    """Type-hinted function."""
    pass

def add_component(
    network: SParameterNetwork,
    component: MatchingComponent
) -> SParameterNetwork:
    """Type-hinted with multiple parameters."""
    pass
```

**Validation with pydantic** (optional, if runtime validation needed):
- Could add pydantic models for stricter validation
- For now, manual validation in constructors/methods is sufficient
- Constitution prioritizes simplicity over heavy frameworks

---

## Testing Considerations

### Unit Test Fixtures

```python
# tests/fixtures/snp_files/simple_antenna.s2p
# Tests/fixtures/components.py
@pytest.fixture
def sample_component():
    return MatchingComponent(
        id="test_comp_1",
        port=1,
        component_type=ComponentType.CAPACITOR,
        value=10e-12,
        placement=PlacementType.SERIES,
        created_at=datetime.utcnow(),
        order=0
    )

@pytest.fixture
def sample_network():
    # Load from fixture SNP file
    from snp_tool.parsers.touchstone import parse_snp
    return parse_snp(Path("tests/fixtures/snp_files/simple_antenna.s2p"))
```

### Validation Tests

```python
def test_port_config_max_5_components():
    """Test FR-003: max 5 components per port."""
    port_config = PortConfiguration(port_number=1, reference_impedance=50.0, components=[])
    
    # Add 5 components (should succeed)
    for i in range(5):
        comp = create_test_component(order=i)
        port_config.add_component(comp)
    
    # Add 6th component (should raise)
    with pytest.raises(ValueError, match="Maximum 5 components"):
        port_config.add_component(create_test_component(order=5))
```

---

## Summary

This data model provides:

1. ✅ **Complete entity definitions** with type-hinted fields
2. ✅ **Clear relationships** (1:N, N:M) between entities
3. ✅ **Validation rules** from functional requirements
4. ✅ **State machines** for network modification and optimization workflows
5. ✅ **Serialization formats** for session persistence
6. ✅ **Computed properties** with caching strategy
7. ✅ **Test fixtures** design for TDD

**Next**: Define API contracts (contracts/cli-interface.md, contracts/core-api.md)
